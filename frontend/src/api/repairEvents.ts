import {request} from './client';
import {RepairSpecimen} from '../types/domain';

export const getRepairEvents=(cohortId:number)=>
  request<RepairSpecimen[]>(`/cohorts/${cohortId}/repair-events`);
