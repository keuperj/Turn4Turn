/** Load browser hooks from the authoritative scenario registry. */
export class ScenarioRenderers {
 constructor(){this.entries=new Map();}
 async load(){
  const response=await fetch('/api/scenarios');
  if(!response.ok)throw new Error(`Scenario registry: HTTP ${response.status}`);
  const catalog=await response.json();
  await Promise.all(catalog.scenarios.map(async entry=>{
   const hooks=await import(entry.module);
   if(!hooks.profile)throw new Error(`Scenario ${entry.id} needs a background profile`);
   this.entries.set(entry.id,hooks);
  }));
 }
 get(id){
  const scenario=this.entries.get(id);
  if(!scenario)throw new Error(`Scenario renderer is not loaded: ${id}`);
  return scenario;
 }
}
