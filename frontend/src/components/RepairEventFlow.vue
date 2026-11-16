<script setup lang="ts">
import {computed, ref, watch} from 'vue';
import {RepairSpecimen} from '../types/domain';
import DataTable from './common/DataTable.vue';
import {number} from '../utils/format';

const props=defineProps<{specimens:RepairSpecimen[]}>();
const pickedId=ref<number>(0);
const current=computed(()=>props.specimens.find(s=>s.specimen_id===pickedId.value)||props.specimens[0]||null);
watch(()=>props.specimens,list=>{if(list.length&&!list.some(s=>s.specimen_id===pickedId.value))pickedId.value=list[0].specimen_id;},{immediate:true});
const kindClass=(k:string)=>({failure:'kind-failure',repair:'kind-repair',withdrawal:'kind-withdrawal'} as Record<string,string>)[k]||'';
const kindCn:Record<string,string>={failure:'故障',repair:'修复',withdrawal:'永久退出'};
// 接收顺序即后端 received_seq 升序，用来体现“乱序到达”；另给出按时间排序的对照
const timeOrdered=computed(()=>current.value?[...current.value.events].sort((a,b)=>a.event_time-b.event_time||a.received_seq-b.received_seq):[]);
const isOutOfOrder=computed(()=>{const c=current.value;return !!c&&c.events.some((e,i)=>timeOrdered.value[i]?.id!==e.id);});
</script>
<template>
  <div class="repair-flow">
    <div class="cohort-header repair-header">
      <label>选择灯带试件（复发事件流）
        <select aria-label="选择灯带试件" :value="current?.specimen_id||0"
          @change="pickedId=Number(($event.target as HTMLSelectElement).value)">
          <option v-for="s in specimens" :key="s.specimen_id" :value="s.specimen_id">
            {{s.code}} · {{s.event_count}} 条记录
          </option>
        </select>
      </label>
      <div>
        <b :class="{'out-of-order':isOutOfOrder}">{{isOutOfOrder?'存在乱序':'时间有序'}}</b>
        <span>接收顺序 vs 事件时间</span>
      </div>
    </div>
    <p class="caption" v-if="current">
      下表按<strong>接收序号</strong>排列（数据到达的真实次序）；事件时间可以乱序，分析时由状态机按事件时间重建。
      试件 {{current.code}} 共 {{current.event_count}} 条故障/修复/退出记录。
    </p>
    <DataTable v-if="current" :head="['接收序号','事件时间 / h','类型','记录备注']">
      <tr v-for="e in current.events" :key="e.id">
        <td class="mono">{{e.received_seq}}</td>
        <td class="mono">{{number(e.event_time,1)}}</td>
        <td><span :class="['event-tag',kindClass(e.kind)]">{{kindCn[e.kind]}}</span></td>
        <td class="note-cell">{{e.note}}</td>
      </tr>
    </DataTable>
  </div>
</template>
