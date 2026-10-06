"""A fixed, server-guided practice mission using the real movement and weapons."""
from game import Game, WEAPONS

LESSONS=[
    dict(title='Move to the marker',text='VEGA is selected. Click Move, then single-click the gold tile to preview the route and its action-point cost. Double-click the same tile (or press Enter after previewing) to move. Moving up to five tiles costs 1 AP.',action='move',x=6,y=15,z=0,controls=['#move-mode'],marker='MOVE HERE'),
    dict(title='Fire your rifle',text='You have 1 AP left and one training round loaded. Click Attack, then click RIFLE TARGET to preview the shot. Double-click it to fire. Rifles use all remaining AP. Training shots always hit; normal missions use the shown hit chance.',action='attack',x=6,y=10,z=0,controls=['#attack-mode'],marker='RIFLE TARGET'),
    dict(title='Start a fresh turn',text='Your action points are spent. Click End squad turn, or press Enter with no preview selected. In real missions, hostiles act before your squad gets fresh AP. These practice targets stay still and never fire.',action='end_turn',controls=['#end']),
    dict(title='Reload the rifle',text='Your rifle is empty. Click Reload (or press R). Reloading moves ammunition from reserve into the magazine and costs 1 AP. Watch the loaded and reserve counts change.',action='reload',controls=['#reload']),
    dict(title='Switch to your sidearm',text='Click M9 in the equipment panel. Switching weapons costs no AP, but requires a fighter who still has AP. The highlighted equipment card shows the weapon you have selected.',action='equip',weapon='M9',controls=['[data-weapon="M9"]']),
    dict(title='Fire the pistol',text='Attack mode is now selected. Preview PISTOL TARGET, then double-click it to fire. A pistol shot costs 1 AP, unlike a rifle shot which uses all remaining AP.',action='attack',x=10,y=13,z=0,controls=['#attack-mode'],marker='PISTOL TARGET'),
    dict(title='Prepare another turn',text='End the squad turn again to restore your 2 AP. In normal missions, check the whole squad before ending a turn: another fighter may still be able to move or fire.',action='end_turn',controls=['#end']),
    dict(title='Select a grenade',text='Click Frag grenade in the equipment panel. Grenades attack a ground point and affect everyone within the blast radius, including your own fighters and civilians.',action='equip',weapon='Frag grenade',controls=['[data-weapon="Frag grenade"]']),
    dict(title='Use the blast preview',text='Click the gold grenade marker near the last two targets. Check the blast radius and affected targets in the preview, then double-click to throw. The marked point is safely away from VEGA. Explosives use all remaining AP.',action='attack',x=11,y=10,z=0,controls=['#attack-mode'],marker='GRENADE HERE'),
]


class TutorialGame(Game):
    """Run a repeatable exercise with guarded actions and harmless targets."""
    def __init__(self):
        """Create the fixed range and pre-equip one trainee."""
        super().__init__(73421,'urban',size=24,mission='eliminate',title='Training range',objective='Learn movement, action points and weapons in a guided practice mission.')
        self.tutorial_step=0
        self.tiles=[['road' if x in (18,19,20) or y in (3,4,5) else 'plaza' for x in range(self.size)] for y in range(self.size)]
        self.heights=[[0]*self.size for _ in range(self.size)]
        self.surfaces={(x,y,0) for y in range(self.size) for x in range(self.size)}
        self.buildings=[];self.props=[];self.walls={};self.blocked=set();self.portals=[];self.ladders=[];self.stairs=[]
        self.scenery.update(road_x=19,cross_y=4,label='Training range')
        vega=self.make_unit('s0','VEGA','soldier',6,18,'M4A1','Trainee')
        vega['inventory']={w:dict(ammo=WEAPONS[w]['capacity'],reserve=12 if w=='M4A1' else 0) for w in ('M4A1','M9','Frag grenade')}
        vega['ammo']=vega['inventory']['M4A1']['ammo']=1
        self.units=[vega]
        for i,(name,x,y,hp) in enumerate([('RIFLE TARGET',6,10,4),('PISTOL TARGET',10,13,2),('BLAST TARGET A',11,10,7),('BLAST TARGET B',12,10,7)]):
            target=self.make_unit(f'e{i}',name,'alien',x,y,None,'Stationary training target')
            target.update(hp=hp,max_hp=hp,ap=0);self.units.append(target)
        self.log=['Welcome to the training range. Follow the gold marker and highlighted controls.','Targets never move or shoot. Training does not affect your mission statistics.']
        self.events=[];self.geometry_revision+=1;self._los_cache.clear();self.init_ai();self.init_fog()

    def chance(self,shooter,target):
        """Keep valid training shots deterministic without changing real missions."""
        chance=super().chance(shooter,target)
        return 100 if chance and shooter['team']=='soldier' else chance

    def check_end(self):
        """Completion is controlled by the final lesson, not intermediate kills."""

    def enemy_turn(self):
        """Restore AP without moving targets or exposing the trainee to damage."""
        self.round+=1
        for unit in self.alive('soldier'):unit.update(ap=self.player_time,overwatch=False)
        self.log.append(f'Round {self.round}: squad action points restored. Practice targets hold position.')
        self.refresh_visibility()

    def validate_lesson(self,data):
        """Reject off-lesson commands before they can consume time or ammunition."""
        if self.status!='active':raise ValueError('Training complete. Replay the tutorial or start a mission.')
        lesson=LESSONS[self.tutorial_step]
        required={k:lesson[k] for k in ('action','x','y','z','weapon') if k in lesson}
        if any(data.get(k)!=v for k,v in required.items()) or data.get('unit')!='s0' or data.get('structure'):
            raise ValueError(f"Training step {self.tutorial_step+1}: {lesson['title']}. Follow the highlighted control and gold marker.")

    def preview(self,data):
        """Use the real preview while keeping the learner on the current task."""
        self.validate_lesson(data)
        return super().preview(data)

    def action(self,data):
        """Advance only after the required gameplay action succeeds."""
        self.validate_lesson(data)
        super().action(data)
        self.log.append(f"Training step {self.tutorial_step+1} complete: {LESSONS[self.tutorial_step]['title']}.")
        self.tutorial_step+=1
        if self.tutorial_step==len(LESSONS):
            self.status='victory';self.log.append('Training complete. You are ready for a single mission or campaign.')

    def state(self):
        """Expose the current lesson and its marker with the authoritative state."""
        state=super().state()
        state['tutorial']=dict(step=self.tutorial_step,total=len(LESSONS),complete=self.tutorial_step==len(LESSONS),
                               lesson=LESSONS[self.tutorial_step] if self.tutorial_step<len(LESSONS) else None)
        return state
