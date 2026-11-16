export interface User{name:string;email:string;role:string}
export interface Cohort{id:number;code:string;name:string;process:string;description:string;specimen_count:number;events:number;censored:number}
export interface Specimen{id:number;code:string;cohort_id:number;material:string;enrolled_at:string;followup_id:number;duration_hours:number;event_observed:boolean;note:string}
export interface CurvePoint{time:number;at_risk:number;events:number;censored:number;survival:number;lower:number;upper:number;greenwood_sum:number}
export interface GroupResult{cohort:Cohort;n:number;events:number;censored:number;curve:CurvePoint[];risk_table:{time:number;at_risk:number}[];median:number|null;median_status:string;last_observed:number;confidence:number;interval_method:string}
export interface Logrank{estimable:boolean;chi_square:number|null;p_value:number|null;observed_a:number;expected_a:number;variance:number;reason:string;event_table:{time:number;risk_a:number;risk_b:number;events_a:number;events_b:number;expected_a:number;variance:number}[]}
export interface Result{groups:GroupResult[];logrank:Logrank;confidence:number;time_unit:string;input_hash:string;interpretation:string;assumptions:string}
export interface Run{id:number;name:string;cohort_a_id:number;cohort_b_id:number;confidence:number;status:string;result:Result;error:string;owner:string;created_at:string}

// —— 复发事件（可修复灯带 MCF）——
export type EventKind='failure'|'repair'|'withdrawal'
export interface RepairEventRow{id:number;specimen_id:number;kind:EventKind;event_time:number;received_seq:number;note:string}
export interface RepairSpecimen{specimen_id:number;code:string;material:string;event_count:number;events:RepairEventRow[]}
export interface WorkInterval{start:number;end:number;exposure:number}
export interface ChainEvent extends RepairEventRow{kind_cn:string;state_after:string;accepted:boolean;isolation_reason:string}
export interface McfPoint{time:number;at_risk:number;events:number;mcf:number;se:number;lower:number;upper:number}
export interface McfBand{band_method:string;n_resamples:number;seed:number;achieved_level:number;grid:number[];base_mcf:number[];lower:number[];upper:number[];estimable:boolean;reason:string}
export interface SpecimenHistory{specimen_id:number;code:string;terminal_state:string;failure_count:number;failure_times:number[];exposure_hours:number;intervals:WorkInterval[];chain:ChainEvent[];censored_while_down:boolean}
export interface QuarantinedSpecimen{specimen_id:number;code:string;isolation_reason:string;isolation_reason_text:string;isolation_event_id:number|null;terminal_state:string;chain:ChainEvent[]}
export interface McfGroup{cohort:Cohort;specimen_total:number;specimen_valid:number;specimen_quarantined:number;n_failures:number;total_exposure_hours:number;curve:McfPoint[];band:McfBand;pointwise_method:string;variance_method:string;last_observed:number;specimen_histories:SpecimenHistory[];quarantined_specimens:QuarantinedSpecimen[]}
export interface McfDifference{grid:number[];mcf_diff:number[];pointwise_lower:number[];pointwise_upper:number[];simultaneous_lower:number[];simultaneous_upper:number[];excludes_zero_everywhere:boolean;band_method:string;pointwise_method:string;n_resamples:number;seed:number}
export interface RecurrentResult{groups:McfGroup[];difference:McfDifference;cutoff_hours:number;confidence:number;time_unit:string;bootstrap_resamples:number;input_hash:string;method_version:string;isolation_reasons:Record<string,string>;interpretation:string;assumptions:string}
export interface RecurrentRun{id:number;name:string;cohort_a_id:number;cohort_b_id:number;cutoff_hours:number;confidence:number;status:string;result:RecurrentResult;error:string;owner:string;created_at:string}

export interface Note{id:number;run_id:number|null;recurrent_run_id:number|null;title:string;interpretation:string;recommendation:string;status:string;owner:string;reviewer:string;review_note:string;created_at:string;reviewed_at:string}
export interface Audit{id:number;actor:string;action:string;target:string;created_at:string}
