// Ordinal triage priority, not a calibrated probability of fire.
export function scoreIncident(stations, visible = false) {
  const alarm = stations.some(s => s.decision === 'ALARM' && s.age_s != null && s.age_s <= 30);
  const incomplete = !stations.length || stations.some(s => s.age_s == null || s.age_s > 30 || s.decision === 'WARNING');
  if (alarm) return {level: 3, label:'ALARM', reason: visible ? 'Sensor alarm and visual evidence in this tour. Inspect the station area.' : 'Fresh sensors indicate possible fire. A visible flame is not required.'};
  if (visible) return {level: 2, label:'INSPECT', reason:'Drone camera detected flame or smoke. Inspect the field of view; station location is unconfirmed.'};
  if (incomplete) return {level: 1, label:'WARNING', reason:'Some sensors are stale, incomplete or unvisited. Continue collection.'};
  return {level: 0, label:'NO ALARM', reason:'Fresh sensor measurements are below the learned threshold.'};
}
