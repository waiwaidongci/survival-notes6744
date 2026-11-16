<script setup lang="ts">
import {computed, ref} from 'vue';
import {useRoute} from 'vue-router';
import {Download, Check} from 'lucide-vue-next';
import {useResearchData} from '../hooks/useResearch';
import {useAuth} from '../stores/auth';
import {useAction} from '../hooks/useAction';
import {createNote, reviewNote} from '../api/notes';
import {download} from '../api/client';
import Notice from '../components/common/Notice.vue';
import RunSummary from '../components/RunSummary.vue';
import RecurrentRunSummary from '../components/RecurrentRunSummary.vue';
import {ReviewStatus} from '../constants/enums';
import {time} from '../utils/format';

const s=useResearchData(),auth=useAuth(),a=useAction(),route=useRoute();
// kind: 'terminal'（旧终态）| 'recurrent'（新MCF）
const kind=ref<'terminal'|'recurrent'>(route.query.recurrent?'recurrent':'terminal');
const terminalId=ref(Number(route.query.run)||0);
const recurrentId=ref(Number(route.query.recurrent)||0);
const title=ref(''),interpretation=ref(''),recommendation=ref('');
const reviews=ref<Record<number,string>>({});

const terminalRuns=computed(()=>s.runs.filter(r=>r.status==='completed'));
const recurrentRuns=computed(()=>s.recurrentRuns.filter(r=>r.status==='completed'));
const terminalRun=computed(()=>terminalRuns.value.find(r=>r.id===terminalId.value)||terminalRuns.value[0]);
const recurrentRun=computed(()=>recurrentRuns.value.find(r=>r.id===recurrentId.value)||recurrentRuns.value[0]);
const activeRun=computed(()=>kind.value==='recurrent'?recurrentRun.value:terminalRun.value);
const notes=computed(()=>{
  if(kind.value==='recurrent')return s.notes.filter(n=>n.recurrent_run_id===recurrentRun.value?.id);
  return s.notes.filter(n=>n.run_id===terminalRun.value?.id);
});

function submit(){
  a.execute(async()=>{
    const payload=kind.value==='recurrent'
      ?{recurrent_run_id:recurrentRun.value!.id,title:title.value,interpretation:interpretation.value,recommendation:recommendation.value}
      :{run_id:terminalRun.value!.id,title:title.value,interpretation:interpretation.value,recommendation:recommendation.value};
    await createNote(payload);
    title.value='';interpretation.value='';recommendation.value='';
    await s.refresh();
  });
}
function review(id:number,status:string){
  a.execute(async()=>{await reviewNote(id,{status,review_note:reviews.value[id]});await s.refresh();});
}
function exportRun(){
  const r=activeRun.value;if(!r)return;
  const path=kind.value==='recurrent'?`/recurrent-runs/${r.id}/export`:`/runs/${r.id}/export`;
  const prefix=kind.value==='recurrent'?'recurrent-mcf-run':'survival-run';
  a.execute(()=>download(path,`${prefix}-${r.id}.csv`));
}
</script>
<template>
  <div class="page">
    <div class="page-title">
      <div>
        <p class="eyebrow">MAINTENANCE RECORD / 05</p>
        <h1>维护建议<span>终态研究与复发研究的证据，分别归档、同一审批口径。</span></h1>
      </div>
    </div>
    <Notice :message="s.error||a.error.value" @retry="s.refresh"/>
    <div class="view-switch">
      <button :class="{active:kind==='terminal'}" @click="kind='terminal'">终态耐久研究（KM / log-rank）</button>
      <button :class="{active:kind==='recurrent'}" @click="kind='recurrent'">复发故障研究（MCF / 同时带）</button>
    </div>
    <label v-if="kind==='terminal'">关联终态研究
      <select aria-label="关联终态研究" :value="terminalRun?.id||''" @change="terminalId=Number(($event.target as HTMLSelectElement).value)">
        <option v-for="r in terminalRuns" :key="r.id" :value="r.id">#{{r.id}} / {{r.name}}</option>
      </select>
    </label>
    <label v-else>关联复发研究
      <select aria-label="关联复发研究" :value="recurrentRun?.id||''" @change="recurrentId=Number(($event.target as HTMLSelectElement).value)">
        <option v-for="r in recurrentRuns" :key="r.id" :value="r.id">#{{r.id}} / {{r.name}}</option>
      </select>
    </label>

    <RunSummary v-if="terminalRun&&kind==='terminal'" :run="terminalRun"/>
    <RecurrentRunSummary v-else-if="recurrentRun&&kind==='recurrent'" :run="recurrentRun"/>

    <div class="notes-grid">
      <section>
        <h2>提交维护观察建议</h2>
        <form v-if="auth.user?.role!=='viewer'" @submit.prevent="submit">
          <label>建议标题<input aria-label="建议标题" v-model="title" minlength="2" required placeholder="例如：两批累计故障负担的维护窗口补充"/></label>
          <label>证据解释<textarea aria-label="证据解释" v-model="interpretation" minlength="8" required placeholder="结合MCF、同时置信带、隔离试件与在险历程说明结果。"/></label>
          <label>维护建议<textarea aria-label="维护建议" v-model="recommendation" minlength="8" required placeholder="记录现场复核与补充观察，不自动决定更换。"/></label>
          <button class="primary" :disabled="a.busy.value||!activeRun">提交负责人确认</button>
        </form>
        <p v-else class="role-note">阅读者可查看维护建议，获负责人确认后可导出研究CSV。</p>
      </section>
      <section class="note-list">
        <h2>确认档案</h2>
        <article v-for="n in notes" :key="n.id">
          <div class="note-title">
            <span class="eyebrow">NOTE-{{n.id}} / {{kind==='recurrent'?'RECURRENT':'RUN'}}-{{n.recurrent_run_id??n.run_id}}</span>
            <span :class="['review-badge',n.status]">{{ReviewStatus[n.status as keyof typeof ReviewStatus]}}</span>
          </div>
          <h3>{{n.title}}</h3>
          <p><b>证据</b>{{n.interpretation}}</p>
          <p><b>建议</b>{{n.recommendation}}</p>
          <small>{{n.owner}} · {{time(n.created_at)}}</small>
          <div v-if="n.status==='submitted'&&auth.user?.role==='admin'" class="approval-form">
            <label>确认意见<textarea :aria-label="'确认意见 '+n.id" v-model="reviews[n.id]" minlength="8" placeholder="至少8字，写明适用范围和确认依据。"/></label>
            <div>
              <button class="primary" :disabled="a.busy.value||(reviews[n.id]||'').length<8" @click="review(n.id,'approved')"><Check :size="14"/>确认归档</button>
              <button class="outline" :disabled="a.busy.value||(reviews[n.id]||'').length<8" @click="review(n.id,'rejected')">退回补充</button>
            </div>
          </div>
          <div v-if="n.status!=='submitted'" class="review-note"><b>{{n.reviewer}}</b><p>{{n.review_note}}</p></div>
          <button v-if="n.status==='approved'" class="text-link" @click="exportRun"><Download :size="14"/>下载获批CSV</button>
        </article>
        <p v-if="!notes.length" class="empty">此研究还没有维护建议。研究员提交后由负责人确认，确认后开放导出。</p>
      </section>
    </div>
  </div>
</template>
