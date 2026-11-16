<script setup lang="ts">
import {computed, ref} from 'vue';
import {useRouter} from 'vue-router';
import {ArrowRight} from 'lucide-vue-next';
import {useResearchData} from '../hooks/useResearch';
import {useAuth} from '../stores/auth';
import {useAction} from '../hooks/useAction';
import {createRecurrentRun} from '../api/recurrentRuns';
import CohortSelector from '../components/CohortSelector.vue';
import Notice from '../components/common/Notice.vue';

const s=useResearchData(),auth=useAuth(),a=useAction(),router=useRouter();
const name=ref(''),aid=ref(0),bid=ref(0),cutoff=ref(1450),confidence=ref(.95);
const ca=computed(()=>aid.value||s.cohorts[0]?.id||0);
const cb=computed(()=>bid.value||s.cohorts[1]?.id||0);
function submit(){
  a.execute(async()=>{
    const r=await createRecurrentRun({name:name.value,cohort_a_id:ca.value,cohort_b_id:cb.value,
      cutoff_hours:cutoff.value,confidence:confidence.value});
    router.push('/recurrent-results?run='+r.id);
  });
}
</script>
<template>
  <div class="page">
    <div class="page-title">
      <div>
        <p class="eyebrow">RECURRENT EVENT PROTOCOL / 07</p>
        <h1>复发故障研究配置<span>维修后继续展出的灯带会多次熄灭，按试件累计各次故障负担。</span></h1>
      </div>
    </div>
    <Notice :message="s.error||a.error.value" @retry="s.refresh"/>
    <div class="editor-grid">
      <form class="research-form" @submit.prevent="submit">
        <div class="form-heading"><span>01</span><h2>定义复发研究</h2></div>
        <label>研究名称
          <input aria-label="研究名称" v-model="name" minlength="2" maxlength="120"
            placeholder="例如：两批灯带维修后累计故障负担比较" required :disabled="auth.user?.role==='viewer'"/>
        </label>
        <CohortSelector :cohorts="s.cohorts" :model-value="ca" label="对照工艺批次" @update:model-value="aid=$event"/>
        <CohortSelector :cohorts="s.cohorts" :model-value="cb" label="比较工艺批次" @update:model-value="bid=$event"/>
        <div class="form-heading second"><span>02</span><h2>固定在险与置信口径</h2></div>
        <label>观察窗右端点 / 小时
          <input aria-label="观察窗右端点" v-model.number="cutoff" type="number" min="1" max="1000000" step="25" required/>
        </label>
        <label>置信水平
          <select v-model.number="confidence" aria-label="置信水平">
            <option :value=".95">95% / bootstrap 同时带</option>
            <option :value=".9">90% / bootstrap 同时带</option>
            <option :value=".99">99% / bootstrap 同时带</option>
          </select>
        </label>
        <div class="protocol-line">
          <span>独立单位</span><b>试件（非各次故障）</b>
          <span>维修期</span><b>不在险</b>
          <span>断裂/退出后事件</span><b>整件隔离</b>
        </div>
        <p class="caption">
          同一试件的多次熄灭是相关重复观测，以试件为单位重抽样估计不确定性；
          乱序到达的故障、修复、永久退出记录会先重建事件链与工作区间，再计算平均累计故障函数（MCF）。
        </p>
        <button v-if="auth.user?.role!=='viewer'" class="primary" :disabled="a.busy.value">
          提交复发研究 <ArrowRight :size="16"/>
        </button>
        <p v-else class="role-note">阅读者可以查看配置，创建复发研究需要研究员权限。</p>
      </form>
      <aside class="method-note">
        <span class="eyebrow">METHOD NOTE / 02</span>
        <h2>复发数据的三条纪律</h2>
        <ol>
          <li><b>不能只记首次故障</b><p>维修后再次熄灭是真实负担，只记首故障会系统性漏掉后续维修成本。</p></li>
          <li><b>不能把各次故障当独立试件</b><p>同一灯带的故障彼此相关，拆开算会人为增大样本量、低估不确定性；重抽样以整件为单位。</p></li>
          <li><b>维修期间不在险</b><p>停机维修与永久退出后的时间不计入在险历程，故障时刻本身仍在险。</p></li>
        </ol>
      </aside>
    </div>
  </div>
</template>
