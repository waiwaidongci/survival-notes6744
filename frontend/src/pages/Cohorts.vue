<script setup lang="ts">
import {computed, ref, watch} from 'vue';
import {useRoute} from 'vue-router';
import {useResearchData} from '../hooks/useResearch';
import {useAuth} from '../stores/auth';
import {useAction} from '../hooks/useAction';
import {annotateFollowup} from '../api/followups';
import CohortSelector from '../components/CohortSelector.vue';
import DataTable from '../components/common/DataTable.vue';
import Notice from '../components/common/Notice.vue';
import RepairEventFlow from '../components/RepairEventFlow.vue';
import {number} from '../utils/format';

const s=useResearchData(),auth=useAuth(),a=useAction(),route=useRoute(),
  selected=ref(Number(route.query.cohort)||0),editing=ref(0),note=ref(''),
  view=ref<'terminal'|'recurrent'>('terminal');
const cohort=computed(()=>s.cohorts.find(c=>c.id===selected.value)||s.cohorts[0]);
watch(()=>cohort.value?.id,id=>{if(id){s.loadSpecimens(id);s.loadRepairSpecimens(id);}},{immediate:true});
watch(view,v=>{if(v==='recurrent'&&cohort.value)s.loadRepairSpecimens(cohort.value.id);});
async function save(){
  await a.execute(async()=>{
    await annotateFollowup(editing.value,note.value);editing.value=0;
    await s.loadSpecimens(cohort.value.id);
  });
}
</script>
<template>
  <div class="page">
    <div class="page-title">
      <div>
        <p class="eyebrow">SPECIMEN & FOLLOW-UP / 02</p>
        <h1>试件与随访<span>终态失效与可修复复发事件，分别记录、各自成链。</span></h1>
      </div>
    </div>
    <Notice :message="s.error||a.error.value" @retry="s.refresh"/>
    <div class="cohort-header">
      <CohortSelector :cohorts="s.cohorts" :model-value="cohort?.id||0" label="工艺批次" @update:model-value="selected=$event"/>
      <div v-if="cohort"><b>{{cohort.events}} / {{cohort.censored}}</b><span>终态失效事件 / 右删失</span></div>
    </div>
    <div class="view-switch">
      <button :class="{active:view==='terminal'}" @click="view='terminal'">终态随访（每件一条）</button>
      <button :class="{active:view==='recurrent'}" @click="view='recurrent'">复发事件流（故障/修复/退出，乱序接收）</button>
    </div>

    <template v-if="view==='terminal'">
      <p class="caption">{{cohort?.description}} 时间单位统一为小时。每个试件只有一条终态观察。</p>
      <form v-if="editing" class="annotation" @submit.prevent="save">
        <label>随访备注<input aria-label="随访备注" v-model="note" minlength="8" required/></label>
        <button class="primary" :disabled="a.busy.value">保存备注</button>
        <button class="outline" type="button" @click="editing=0">取消</button>
      </form>
      <DataTable :head="['试件编号','材料','时长 / h','观察状态','终态备注','操作']">
        <tr v-for="row in s.specimens" :key="row.id">
          <td class="mono">{{row.code}}</td><td>{{row.material}}</td>
          <td>{{number(row.duration_hours,0)}}</td>
          <td><span :class="['event-tag',row.event_observed?'event':'censored']">{{row.event_observed?'失效事件':'右删失'}}</span></td>
          <td>{{row.note}}</td>
          <td><button v-if="auth.user?.role!=='viewer'" class="text-link" @click="editing=row.followup_id;note=row.note">补充备注</button></td>
        </tr>
      </DataTable>
    </template>

    <RepairEventFlow v-else :specimens="s.repairSpecimens"/>
  </div>
</template>
