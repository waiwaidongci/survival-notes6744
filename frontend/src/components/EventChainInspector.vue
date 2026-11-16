<script setup lang="ts">
import {computed, ref} from 'vue';
import {McfGroup, ChainEvent} from '../types/domain';
import DataTable from './common/DataTable.vue';
import {number} from '../utils/format';

const props=defineProps<{group:McfGroup}>();
const tab=ref<'quarantine'|'history'|'chain'>('quarantine');
const pickedHistory=ref<number|null>(null);
const pickedChain=ref<number|null>(null);

const kindClass=(k:string)=>({failure:'kind-failure',repair:'kind-repair',withdrawal:'kind-withdrawal'} as Record<string,string>)[k]||'';
const histories=computed(()=>props.group.specimen_histories);
const currentHistory=computed(()=>histories.value.find(h=>h.specimen_id===pickedHistory.value)||null);
const currentQuarantine=computed(()=>props.group.quarantined_specimens.find(q=>q.specimen_id===pickedChain.value)||null);

function chainRows(chain:ChainEvent[]){
  // 已按 (event_time, received_seq) 重建排序；同时标注接收序号以体现乱序
  return [...chain].sort((a,b)=>a.event_time-b.event_time||a.received_seq-b.received_seq);
}
</script>
<template>
  <div class="chain-inspector">
    <div class="inspector-tabs">
      <button :class="{active:tab==='quarantine'}" @click="tab='quarantine'">
        隔离试件（{{group.specimen_quarantined}}）
      </button>
      <button :class="{active:tab==='history'}" @click="tab='history'">
        在险历程（{{group.specimen_valid}}）
      </button>
    </div>

    <template v-if="tab==='quarantine'">
      <p class="caption" v-if="!group.quarantined_specimens.length">本批没有被隔离的试件，事件链全部闭合。</p>
      <DataTable v-else :head="['试件编号','触发事件','隔离原因代码','隔离原因说明','终态','事件链']">
        <tr v-for="q in group.quarantined_specimens" :key="q.specimen_id">
          <td class="mono">{{q.code}}</td>
          <td>#{{q.isolation_event_id ?? '—'}}</td>
          <td class="mono">{{q.isolation_reason}}</td>
          <td>{{q.isolation_reason_text}}</td>
          <td><span class="event-tag quarantine">{{q.terminal_state}}</span></td>
          <td><button class="text-link" @click="pickedChain=q.specimen_id;tab='chain'">查看事件链 →</button></td>
        </tr>
      </DataTable>
    </template>

    <template v-else-if="tab==='history'">
      <DataTable :head="['试件编号','终态','故障次数','在险小时','末次仍停机','工作区间数','详情']">
        <tr v-for="h in histories" :key="h.specimen_id">
          <td class="mono">{{h.code}}</td>
          <td><span class="event-tag" :class="h.terminal_state==='withdrawn'?'censored':'event'">{{h.terminal_state}}</span></td>
          <td>{{h.failure_count}}</td>
          <td>{{number(h.exposure_hours,1)}}</td>
          <td>{{h.censored_while_down?'是（停机不在险）':'否'}}</td>
          <td>{{h.intervals.length}}</td>
          <td><button class="text-link" @click="pickedHistory=h.specimen_id">在险历程 →</button></td>
        </tr>
      </DataTable>
    </template>

    <template v-else>
      <button class="outline back-btn" @click="tab=pickedChain!==null?'quarantine':'history'">← 返回列表</button>
      <div v-if="currentQuarantine" class="chain-detail">
        <h3>{{currentQuarantine.code}} · 整件隔离</h3>
        <p class="caption">{{currentQuarantine.isolation_reason_text}}（{{currentQuarantine.isolation_reason}}）</p>
        <DataTable :head="['接收序号','事件时间 / h','类型','重建后状态','是否采纳','隔离原因']">
          <tr v-for="e in chainRows(currentQuarantine.chain)" :key="e.id">
            <td class="mono">{{e.received_seq}}</td>
            <td class="mono">{{number(e.event_time,1)}}</td>
            <td><span :class="['event-tag',kindClass(e.kind)]">{{e.kind_cn}}</span></td>
            <td>{{e.state_after}}</td>
            <td :class="e.accepted?'accepted':'rejected'">{{e.accepted?'采纳':'隔离'}}</td>
            <td>{{e.isolation_reason||'—'}}</td>
          </tr>
        </DataTable>
      </div>
    </template>

    <!-- 在险历程抽屉（行内展开） -->
    <div v-if="currentHistory" class="chain-detail history-detail">
      <div class="section-heading">
        <h3>{{currentHistory.code}} 的工作区间与事件链</h3>
        <button class="text-link" @click="pickedHistory=null">收起 ✕</button>
      </div>
      <DataTable :head="['工作区间起 / h','止 / h','区间在险小时']">
        <tr v-for="(iv,i) in currentHistory.intervals" :key="i">
          <td class="mono">{{number(iv.start,1)}}</td>
          <td class="mono">{{number(iv.end,1)}}</td>
          <td class="mono">{{number(iv.exposure,1)}}</td>
        </tr>
      </DataTable>
      <p class="caption">累计在险 {{number(currentHistory.exposure_hours,1)}} 小时；维修停机与退出后时间不计入。故障时刻本身在险。</p>
      <DataTable :head="['接收序号','事件时间 / h','类型','重建后状态','是否采纳']">
        <tr v-for="e in chainRows(currentHistory.chain)" :key="e.id">
          <td class="mono">{{e.received_seq}}</td>
          <td class="mono">{{number(e.event_time,1)}}</td>
          <td><span :class="['event-tag',kindClass(e.kind)]">{{e.kind_cn}}</span></td>
          <td>{{e.state_after}}</td>
          <td :class="e.accepted?'accepted':'rejected'">{{e.accepted?'采纳':'隔离'}}</td>
        </tr>
      </DataTable>
    </div>
  </div>
</template>
