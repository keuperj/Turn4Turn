"""Private team intelligence, coordinated routes, and independent escape planning."""
import heapq
import math
from collections import deque

from scenarios.common import edge_key


class TacticalAI:
    """Plan from observed contacts; keep all intelligence outside public unit records."""

    def init_ai(self):
        """Create mission-local memories and persistent movement objectives."""
        self.enemy_contacts = {}
        self.enemy_plans = {}
        self.civilian_contacts = {}
        self.civilian_plans = {}

    def observe_contacts(self, observers, targets, memory):
        """Remember snapshots, expiring old or visibly vacated contact locations."""
        visible = {t['id']: t for t in targets
                   if any(self.sees(observer, t) for observer in observers)}
        for uid, contact in list(memory.items()):
            inspected = any(self.sees(observer, contact) for observer in observers)
            if self.round-contact['round'] > 3 or (uid not in visible and inspected):
                del memory[uid]
        for uid, target in visible.items():
            memory[uid] = {key: target[key] for key in
                           ('id', 'team', 'x', 'y', 'z', 'stance', 'weapon', 'hp')}
            memory[uid]['round'] = self.round
        return visible

    def observe_ai(self):
        """Share hostile sightings immediately; each civilian observes independently."""
        if not hasattr(self, 'enemy_contacts'):
            return
        targets = self.alive('soldier')
        if self.mission == 'rescue':
            targets += self.alive('civilian')
        self.observe_contacts(self.alive('alien'), targets, self.enemy_contacts)
        for civilian in self.alive('civilian'):
            memory = self.civilian_contacts.setdefault(civilian['id'], {})
            self.observe_contacts([civilian], self.alive('alien'), memory)

    def ai_neighbors(self, position, unit, doors=False):
        """Yield legal terrain links, accounting for doors, fire, stairs and stance."""
        x, y, z = position
        candidates = [(x+1,y,z), (x-1,y,z), (x,y+1,z), (x,y-1,z)]
        if unit['stance'] != 'prone':
            for a, b in self.stairs+self.ladders:
                if position == tuple(a): candidates.append(tuple(b))
                if position == tuple(b): candidates.append(tuple(a))
        fire = {(f['x'], f['y'], f['z']) for f in self.fires}
        for dest in candidates:
            if dest not in self.surfaces or dest in self.blocked or dest in fire:
                continue
            if dest[2] == 0 and self.tiles[dest[1]][dest[0]] in ('low', 'high'):
                continue
            if dest[2] == z and not self.passable(position, dest, doors):
                continue
            yield dest

    def ai_routes(self, unit):
        """Find whole-map routes, charging closed doors an extra action of travel."""
        start = self.position(unit)
        occupied = {self.position(u) for u in self.alive() if u != unit and
                    (u['team'] == unit['team'] or self.sees(unit, u))}
        costs, previous, queue = {start: 0}, {}, [(0, start)]
        while queue:
            cost, pos = heapq.heappop(queue)
            if cost != costs[pos]: continue
            for dest in self.ai_neighbors(pos, unit, doors=True):
                if dest in occupied: continue
                wall = self.walls.get(edge_key(pos, dest))
                step = 1 + (self.speed(unit) if wall and wall['kind']=='door' and not wall['open'] else 0)
                total = cost+step
                if total < costs.get(dest, math.inf):
                    costs[dest], previous[dest] = total, pos
                    heapq.heappush(queue, (total, dest))
        return costs, previous

    @staticmethod
    def ai_distance(a, b):
        """Measure approximate tactical distance across floors."""
        return abs(a[0]-b[0])+abs(a[1]-b[1])+3*abs(a[2]-b[2])

    def ai_path(self, start, destination, previous):
        """Reconstruct a route from the navigation tree."""
        path = []
        while destination != start:
            path.append(destination)
            destination = previous[destination]
        return list(reversed(path))

    def plan_enemy(self, enemy, assigned, reserved):
        """Assign distinct objectives and compare routes over three hostile phases."""
        costs, previous = self.ai_routes(enemy)
        start = self.position(enemy)
        old = self.enemy_plans.get(enemy['id'], {})
        contacts = list(self.enemy_contacts.values())
        target = None
        if contacts:
            def priority(contact):
                """Balance mission value, distance, and teammates already committed."""
                return (self.ai_distance(start, self.position(contact)) +
                        assigned.get(contact['id'], 0)*7 -
                        (5 if self.mission=='rescue' and contact['team']=='civilian' else 0) -
                        (3 if old.get('target') == contact['id'] else 0))
            target = min(contacts, key=priority)
            slot = assigned.get(target['id'], 0)
            assigned[target['id']] = slot+1
            role = ('support', 'flank_left', 'flank_right')[slot % 3]
            goal = self.position(target)
        else:
            role, slot = 'search', 0
            goal = old.get('goal')
            if goal not in costs or goal == start or self.round-old.get('round', 0)>3:
                choices = sorted(p for p in costs if p not in reserved and costs[p]>3)
                goal = self.rng.choice(choices) if choices else start
        if self.mission == 'defend_flag' and self.flag:
            role, goal = 'advance', self.position(self.flag)
        elif self.mission == 'capture_flag' and self.flag and not target:
            role, goal = 'guard', self.position(self.flag)
        # Stage a flank on opposite sides of the contact, with support facing it.
        anchor = goal
        if target and role.startswith('flank'):
            dx, dy = start[0]-goal[0], start[1]-goal[1]
            side = -1 if role=='flank_left' else 1
            anchor = (goal[0]+(side*4 if abs(dy)>=abs(dx) else 0),
                      goal[1]+(side*4 if abs(dx)>abs(dy) else 0), goal[2])
        horizon = max(1, self.speed(enemy)*self.enemy_time*3)
        candidates = [p for p in costs if p not in reserved and costs[p]<=horizon]
        if not candidates: candidates = [start]
        # Whole-map navigation supplies a route beyond the tactical horizon. Use
        # its tree distance so U-shaped rooms do not trap a greedy distance score.
        strategic = min(costs, key=lambda p:(self.ai_distance(p, anchor), costs[p], p))
        trunk = {start, *self.ai_path(start, strategic, previous)}
        remaining = {}
        for pos in candidates:
            junction = pos
            while junction not in trunk:
                junction = previous[junction]
            remaining[pos] = costs[pos]+costs[strategic]-2*costs[junction]
        remaining.setdefault(start, costs[strategic])
        candidates = sorted(candidates, key=lambda p:(remaining[p], costs[p], p))[:32]
        if start not in candidates: candidates.append(start)
        threats = [c for c in contacts if c['team']=='soldier']
        def score(pos):
            """Value future fire positions, progress and cover at intervening turn ends."""
            hypothetical = dict(enemy, x=pos[0], y=pos[1], z=pos[2])
            value = -4*remaining[pos]-costs[pos]*.35
            if target and role not in ('advance', 'guard'):
                value += self.chance(hypothetical, target)*.6
            path = self.ai_path(start, pos, previous)
            stride = max(1, self.speed(enemy)*self.enemy_time)
            # Penalize exposure on the way, not just at the final destination.
            stops = path[stride-1::stride]+[pos]
            for turn, point in enumerate(stops[:3]):
                future = dict(enemy, x=point[0], y=point[1], z=point[2])
                risk = max((self.chance(t, future) for t in threats), default=0)
                value -= risk*.18*(.8**turn)
            if old.get('destination') == pos: value += 4
            return value
        destination = max(candidates, key=score)
        plan = dict(role=role, target=target['id'] if target else None, goal=goal,
                    destination=destination, route=self.ai_path(start, destination, previous),
                    round=self.round)
        self.enemy_plans[enemy['id']] = plan
        reserved.add(destination)
        return plan

    def follow_enemy_route(self, enemy, route, budget):
        """Execute only affordable route steps; doors and interrupted moves cost AP."""
        remaining = min(budget, enemy['ap'])
        route = list(route)
        while route and remaining > 0 and enemy['hp'] > 0:
            prefix, door, previous = [], None, self.position(enemy)
            for pos in route[:self.speed(enemy)*remaining]:
                if pos not in set(self.ai_neighbors(previous, enemy, doors=True)): break
                wall = self.walls.get(edge_key(previous, pos))
                if wall and wall['kind']=='door' and not wall['open']:
                    door = wall
                    break
                if any(self.position(u)==pos for u in self.alive() if u!=enemy): break
                prefix.append(pos)
                previous = pos
            if prefix:
                self.move(enemy, prefix)
                spent = math.ceil(len(prefix)/self.speed(enemy))
                enemy['ap'] -= spent
                remaining -= spent
                route = route[len(prefix):]
                if enemy['hp']<=0 or self.position(enemy)!=prefix[-1]: break
            if door and remaining > 0 and enemy['hp'] > 0:
                self.toggle_portal(enemy, door)
                remaining -= 1
                self.observe_ai()
            elif not prefix:
                break
        return route

    def coordinated_enemy_turn(self):
        """Share contacts, allocate objectives, then replan after every fighter acts."""
        from game import WEAPONS
        self.observe_ai()
        assigned, reserved = {}, set()
        for enemy in self.alive('alien'):
            if not self.alive('soldier'): break
            self.observe_ai()
            enemy['overwatch'], enemy['ap'] = False, self.enemy_time
            if not enemy['ammo']:
                self.spend_ammo(enemy, -WEAPONS[enemy['weapon']]['capacity'])
                enemy['ap'] -= 1
            if enemy['ap'] <= 0: continue
            plan = self.plan_enemy(enemy, assigned, reserved)
            targets = self.alive('soldier')+(self.alive('civilian') if self.mission=='rescue' else [])
            visible = [t for t in targets if self.chance(enemy, t)]
            best = max(visible, key=lambda t:self.chance(enemy,t), default=None)
            # Support supplies covering fire; flankers advance if a move still allows a shot.
            advance = plan['role']=='advance'
            if plan['route'] and (advance or best is None or self.chance(enemy,best)<55 or
                                  (plan['role'].startswith('flank') and enemy['ap']>1)):
                contact = self.enemy_contacts.get(plan['target'])
                endpoint = dict(enemy, x=plan['destination'][0], y=plan['destination'][1], z=plan['destination'][2])
                can_shoot_after = contact and self.chance(endpoint, contact) and len(plan['route']) <= self.speed(enemy)*(enemy['ap']-1)
                reserve = 1 if not advance and (best is not None or can_shoot_after) else 0
                self.follow_enemy_route(enemy, plan['route'], enemy['ap']-reserve)
            if enemy['hp']<=0: continue
            self.observe_ai()
            if advance and self.position(enemy)==self.position(self.flag): break
            visible = [t for t in targets if t['hp']>0 and not t.get('evacuated') and self.chance(enemy,t)]
            if enemy['ap']>0 and visible:
                best = max(visible, key=lambda t:self.chance(enemy,t)+
                           (12 if t['id']==plan['target'] else 0))
                self.fire(enemy,best)
            elif enemy['ammo']:
                enemy['overwatch'] = True
            enemy['ap'] = 0
            self.observe_ai()

    def civilian_exit_distances(self, civilian):
        """Measure actual escape routes, including detours and vertical links."""
        exits = sorted(p for p in self.surfaces if p[1]==self.size-1 and p[2]==0
                       and p not in self.blocked and self.tiles[p[1]][p[0]] not in ('low','high')
                       and not any((f['x'],f['y'],f['z'])==p for f in self.fires))
        distances, queue = {p:0 for p in exits}, deque(exits)
        while queue:
            pos = queue.popleft()
            for dest in self.ai_neighbors(pos, civilian):
                if dest not in distances:
                    distances[dest] = distances[pos]+1
                    queue.append(dest)
        return distances

    def plan_civilian(self, civilian):
        """Search three independent turns of escape, detour or hiding in place."""
        from game import WEAPONS
        memory = self.civilian_contacts.setdefault(civilian['id'], {})
        self.observe_contacts([civilian], self.alive('alien'), memory)
        threats = list(memory.values())
        distances = self.civilian_exit_distances(civilian)
        start = self.position(civilian)
        occupied = {self.position(u) for u in self.alive() if u!=civilian and self.sees(civilian,u)}
        risk_cache, moves_cache = {}, {}
        def risk(pos):
            """Estimate exposure only to this civilian's remembered threats."""
            if pos not in risk_cache:
                hypothetical = dict(civilian, x=pos[0], y=pos[1], z=pos[2])
                risk_cache[pos] = sum((self.chance(t,hypothetical)/100*WEAPONS[t['weapon']]['damage']*5+
                                      (3 if self.sees(t,hypothetical) else 0))*
                                     (.7**(self.round-t['round'])) for t in threats)
            return risk_cache[pos]
        def moves(pos):
            """Enumerate two-step choices, including waiting and traversed exposure."""
            if pos not in moves_cache:
                paths, queue = {pos:[]}, deque([pos])
                while queue:
                    point = queue.popleft()
                    if len(paths[point])>=2: continue
                    for dest in self.ai_neighbors(point,civilian):
                        if dest in paths or dest in occupied: continue
                        paths[dest] = paths[point]+[dest]
                        queue.append(dest)
                moves_cache[pos] = paths
            return moves_cache[pos]
        # Beam states hold a future endpoint and the first executable move.
        beam = [(0., start, [], [])]
        for depth in range(3):
            best_by_position = {}
            for value, pos, first, future in beam:
                options = {pos:[]} if pos[1]==self.size-1 and pos[2]==0 else moves(pos)
                for dest, path in options.items():
                    progress = distances.get(pos,self.size*4)-distances.get(dest,self.size*4)
                    exposure = risk(dest)+sum(risk(p) for p in path)*.25
                    reward = progress*2-exposure-(.1 if path else 0)
                    if dest[1]==self.size-1 and dest[2]==0: reward += 30
                    total = value+reward*(.8**depth)
                    candidate = (total,dest,path if depth==0 else first,future+[dest])
                    if dest not in best_by_position or total>best_by_position[dest][0]:
                        best_by_position[dest] = candidate
            beam = sorted(best_by_position.values(), key=lambda v:v[0], reverse=True)[:16]
        _, destination, path, future = max(beam,key=lambda v:v[0])
        plan = dict(strategy='escape' if distances.get(destination,math.inf)<distances.get(start,math.inf)
                    else 'hide', route=path, future=future, round=self.round)
        self.civilian_plans[civilian['id']] = plan
        return plan

    def civilian_turn(self):
        """Execute independent escape/hiding decisions without sharing any knowledge."""
        for civilian in self.alive('civilian'):
            plan = self.plan_civilian(civilian)
            self.move(civilian, plan['route'])
            if civilian['y']==self.size-1 and civilian['z']==0:
                civilian['evacuated'] = True
                self.emit(dict(type='evacuate',unit=civilian['id']),civilian)
                self.log.append(f"{civilian['name']} reaches the evacuation boundary.")

    def patrol(self, enemy):
        """Use shared observed contacts for search rather than hidden target positions."""
        self.observe_ai()
        plan = self.plan_enemy(enemy, {}, set())
        self.follow_enemy_route(enemy, plan['route'], enemy['ap'])
        if enemy['hp']>0: enemy['overwatch'], enemy['ap'] = True, 0

    def advance_enemy(self, enemy, goal):
        """Follow a complete terrain route toward an objective, opening doors en route."""
        costs, previous = self.ai_routes(enemy)
        destination = min(costs,key=lambda p:(self.ai_distance(p,goal),costs[p]))
        self.follow_enemy_route(enemy,self.ai_path(self.position(enemy),destination,previous),enemy['ap'])
