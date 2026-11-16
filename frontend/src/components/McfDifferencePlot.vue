<script setup lang="ts">
import {computed, ref} from 'vue';
import {McfDifference} from '../types/domain';
import {number} from '../utils/format';

const props=defineProps<{diff:McfDifference;cutoff:number}>();
const mode=ref<'simultaneous'|'pointwise'>('simultaneous');
const W=940,H=260,PAD_L=65,PAD_R=60,TOP=20,BOTTOM=42;
const maximum=computed(()=>Math.max(props.cutoff,...props.diff.grid));
const allVals=computed(()=>[...props.diff.simultaneous_lower,...props.diff.simultaneous_upper,...props.diff.mcf_diff,0]);
const lo=computed(()=>Math.min(...allVals.value));
const hi=computed(()=>Math.max(...allVals.value));
const pad=computed(()=>(hi.value-lo.value)*0.12||1);
const yMin=computed(()=>lo.value-pad.value),yMax=computed(()=>hi.value+pad.value);
const x=(v:number)=>PAD_L+v/maximum.value*(W-PAD_L-PAD_R);
const y=(v:number)=>TOP+(H-TOP-BOTTOM)*(1-(v-yMin.value)/(yMax.value-yMin.value));
const zeroY=computed(()=>y(0));

function line(key:'mcf_diff'|'pointwise_lower'|'pointwise_upper'|'simultaneous_lower'|'simultaneous_upper'){
  const arr=props.diff[key];
  if(!arr.length)return '';
  let d=`M${x(0)},${y(0)}`;
  props.diff.grid.forEach((t,i)=>{d+=`H${x(t)}V${y(arr[i])}`;});
  return d;
}
function area(){
  const up=mode.value==='simultaneous'?props.diff.simultaneous_upper:props.diff.pointwise_upper;
  const lw=mode.value==='simultaneous'?props.diff.simultaneous_lower:props.diff.pointwise_lower;
  let top=`M${x(0)},${y(0)}`;
  props.diff.grid.forEach((t,i)=>{top+=`H${x(t)}V${y(up[i])}`;});
  let bot='';
  for(let i=props.diff.grid.length-1;i>=0;i--){bot+=`V${y(lw[i])}H${x(props.diff.grid[i])}`;}
  return top+`L${x(props.diff.grid.at(-1)!)},${y(lw.at(-1)!)}`+bot+'Z';
}
const yTicks=computed(()=>Array.from({length:5},(_,i)=>yMin.value+(yMax.value-yMin.value)*i/4));
</script>
<template>
  <section class="survival-plot diff-plot">
    <div class="plot-toolbar">
      <h3>两批 MCF 差值（A − B）与置信带</h3>
      <button :class="{active:mode==='simultaneous'}" @click="mode='simultaneous'">同时带</button>
      <button :class="{active:mode==='pointwise'}" @click="mode='pointwise'">逐点区间</button>
    </div>
    <svg :viewBox="`0 0 ${W} ${H}`" aria-label="MCF差值与同时置信带">
      <g v-for="v in yTicks" :key="v">
        <line :x1="PAD_L" :x2="W-PAD_R" :y1="y(v)" :y2="y(v)" class="gridline"/>
        <text :x="PAD_L-11" :y="y(v)+4" text-anchor="end">{{number(v,2)}}</text>
      </g>
      <line :x1="PAD_L" :x2="W-PAD_R" :y1="zeroY" :y2="zeroY" class="zero-line"/>
      <path :d="area()" class="confidence-band diff-band"/>
      <path :d="line('mcf_diff')" class="survival-line diff-line"/>
      <text :x="W-PAD_R" :y="zeroY-6" text-anchor="end" class="zero-label">差值 0</text>
    </svg>
    <div class="plot-legend">
      <span class="legend-diff"><i/>MCF(A) − MCF(B)</span>
      <small>{{mode==='simultaneous'?'同时带覆盖整条曲线，全程不含零才支持稳定差异':'逐点分位数区间，仅对单个时点成立'}}</small>
    </div>
  </section>
</template>
