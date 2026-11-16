import {defineStore} from 'pinia';
import {ref} from 'vue';
import {Cohort,Specimen,Run,RecurrentRun,RepairSpecimen,Note,Audit} from '../types/domain';
import {getCohorts} from '../api/cohorts';
import {getSpecimens} from '../api/specimens';
import {getRuns} from '../api/runs';
import {getRecurrentRuns} from '../api/recurrentRuns';
import {getRepairEvents} from '../api/repairEvents';
import {getNotes} from '../api/notes';
import {getAudits} from '../api/audits';

export const useResearch=defineStore('research',()=>{
  const cohorts=ref<Cohort[]>([]),
    specimens=ref<Specimen[]>([]),
    runs=ref<Run[]>([]),
    recurrentRuns=ref<RecurrentRun[]>([]),
    repairSpecimens=ref<RepairSpecimen[]>([]),
    notes=ref<Note[]>([]),
    audits=ref<Audit[]>([]),
    error=ref('');

  async function refresh(){
    try{
      const [c,r,rr,n,a]=await Promise.all([
        getCohorts(),getRuns(),getRecurrentRuns(),getNotes(),getAudits()]);
      cohorts.value=c;runs.value=r;recurrentRuns.value=rr;notes.value=n;audits.value=a;
      error.value='';
    }catch(e){error.value=(e as Error).message;}
  }
  async function loadSpecimens(id:number){
    try{specimens.value=await getSpecimens(id);}catch(e){error.value=(e as Error).message;}
  }
  async function loadRepairSpecimens(id:number){
    try{repairSpecimens.value=await getRepairEvents(id);}catch(e){error.value=(e as Error).message;}
  }
  return {cohorts,specimens,runs,recurrentRuns,repairSpecimens,notes,audits,error,
    refresh,loadSpecimens,loadRepairSpecimens};
});
