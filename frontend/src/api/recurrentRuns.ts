import {request} from './client';
import {RecurrentRun} from '../types/domain';

export const getRecurrentRuns=()=>request<RecurrentRun[]>('/recurrent-runs');
export const createRecurrentRun=(data:{name:string;cohort_a_id:number;cohort_b_id:number;cutoff_hours:number;confidence:number})=>
  request<RecurrentRun>('/recurrent-runs',{method:'POST',body:JSON.stringify(data)});
