<script setup lang="ts">
import {computed, ref} from 'vue';
import {RecurrentResult, McfPoint} from '../types/domain';
import {number} from '../utils/format';

const props=defineProps<{result:RecurrentResult}>();
const showBand=ref(true);
const W=940,H=280,PAD_L=65,PAD_R=60,TOP=20,BOTTOM=42;
const maximum=computed(()=>Math.max(props.result.cutoff_hours,...props.result.groups.flatMap(g=>g.curve.map(p=>p.time))));
const maxMcf=computed(()=>Math.max(1,...props.result.groups.flatMap(g=>g.band.upper.length?g.band.upper:g.curve.map(p=>p.mcf)))*1.08);
const x=(v:number)=>PAD_L+v/maximum.value*(W-PAD_L-PAD_R);
const y=(v:number)=>TOP+(H-TOP-BOTTOM)*(1-v/maxMcf.value);

function step(points:McfPoint[],key:'mcf'|'lower'|'upper'){
  if(!points.length)return '';
  let d=`M${x(0)},${y(points[0][key])}`;
  for(const p of points.slice(1))d+=`H${x(p.time)}V${y(p[key])}`;
  return d;
}
// 同时带是按事件网格的逐点值，画成阶梯填充区域
function bandArea(grid:number[],lower:number[],upper:number[]){
  if(!grid.length)return '';
  let top=`M${x(0)},${y(0)}`;
  for(let i=0;i<grid.length;i++){top+=`H${x(grid[i])}V${y(upper[i])}`;}
  let bot='';
  for(let i=grid.length-1;i>=0;i--){bot+=`V${y(lower[i])}H${x(grid[i])}`;}
  return top+`L${x(grid[grid.length-1])},${y(lower[lower.length-1])}`+bot+'Z';
}
const yTicks=computed(()=>{const n=4;return Array.from({length:n+1},(_,i)=>maxMcf.value*i/n);});
const xTicks=computed(()=>{const step=maximum.value/4;return Array.from({length:5},(_,i)=>Math.round(step*i));});
</script>
<template>
  <section class="survival-plot mcf-plot">
    <div class="plot-toolbar">
      <h3>平均累计故障函数 MCF（每件平均熄灭次数）</h3>
      <button :class="{active:showBand}" @click="showBand=!showBand">
        {{Math.round(result.confidence*100)}}% 同时置信带 {{showBand?'显示中':'已隐藏'}}
      </button>
    </div>
    <svg :viewBox="`0 0 ${W} ${H}`" aria-label="两批平均累计故障函数曲线">
      <g v-for="v in yTicks" :key="v">
        <line :x1="PAD_L" :x2="W-PAD_R" :y1="y(v)" :y2="y(v)" class="gridline"/>
        <text :x="PAD_L-11" :y="y(v)+4" text-anchor="end">{{number(v,2)}}</text>
      </g>
      <g v-for="(g,i) in result.groups" :key="g.cohort.id" :class="'curve-'+i">
        <path v-if="showBand&&g.band.estimable" :d="bandArea(g.band.grid,g.band.lower,g.band.upper)" class="confidence-band"/>
        <path :d="step(g.curve,'mcf')" class="survival-line"/>
      </g>
      <text v-for="v in xTicks" :key="v" :x="x(v)" :y="H-18" text-anchor="middle">{{v}}</text>
      <text :x="W-PAD_R+5" :y="H-18">小时</text>
    </svg>
    <div class="plot-legend">
      <span v-for="(g,i) in result.groups" :key="g.cohort.id" :class="'legend-'+i"><i/>{{g.cohort.name}}</span>
      <small>阶梯在故障事件处上升 · 维修不上升 · 带为bootstrap同时带（{{result.bootstrap_resamples}}次试件重抽样）</small>
    </div>
  </section>
</template>
