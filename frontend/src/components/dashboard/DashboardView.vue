<template>
  <div class="dashboard-view">
    <!-- 顶部指标卡片 -->
    <el-row :gutter="16" class="metric-cards">
      <el-col :xs="12" :sm="6" :md="6" :lg="3">
        <div class="metric-card emotion-card" :class="emotionPhaseClass">
          <div class="metric-icon">
            <span class="phase-emoji">{{ phaseEmoji }}</span>
          </div>
          <div class="metric-content">
            <div class="metric-label">情绪周期</div>
            <div class="metric-value">{{ emotionPhase }}</div>
            <div class="metric-score">{{ emotionScore }}分</div>
          </div>
        </div>
      </el-col>

      <el-col :xs="12" :sm="6" :md="6" :lg="3">
        <div class="metric-card limit-up-card">
          <div class="metric-icon text-red">
            <el-icon :size="28"><Top /></el-icon>
          </div>
          <div class="metric-content">
            <div class="metric-label">涨停</div>
            <div class="metric-value text-red">{{ limitUpCount }}</div>
            <div class="metric-sub">连板 {{ continuousCount }}</div>
          </div>
        </div>
      </el-col>

      <el-col :xs="12" :sm="6" :md="6" :lg="3">
        <div class="metric-card limit-down-card">
          <div class="metric-icon text-green">
            <el-icon :size="28"><Bottom /></el-icon>
          </div>
          <div class="metric-content">
            <div class="metric-label">跌停</div>
            <div class="metric-value text-green">{{ limitDownCount }}</div>
            <div class="metric-sub">炸板率 {{ brokenRate }}%</div>
          </div>
        </div>
      </el-col>

      <el-col :xs="12" :sm="6" :md="6" :lg="3">
        <div class="metric-card north-card" :class="northFlowClass">
          <div class="metric-icon">
            <el-icon :size="28"><TrendCharts /></el-icon>
          </div>
          <div class="metric-content">
            <div class="metric-label">北向资金</div>
            <div class="metric-value" :class="northFlowClass">{{ northFlowText }}</div>
            <div class="metric-sub">5日均 {{ northFlow5d }}亿</div>
          </div>
        </div>
      </el-col>

      <el-col :xs="12" :sm="6" :md="6" :lg="3">
        <div class="metric-card position-card">
          <div class="metric-icon">
            <el-icon :size="28"><Wallet /></el-icon>
          </div>
          <div class="metric-content">
            <div class="metric-label">建议仓位</div>
            <div class="metric-value">{{ maxPosition }}%</div>
            <div class="metric-sub">单票 {{ singlePosition }}%</div>
          </div>
        </div>
      </el-col>

      <el-col :xs="12" :sm="6" :md="6" :lg="3">
        <div class="metric-card signal-card">
          <div class="metric-icon text-warning">
            <el-icon :size="28"><Bell /></el-icon>
          </div>
          <div class="metric-content">
            <div class="metric-label">今日信号</div>
            <div class="metric-value">{{ signalCount }}</div>
            <div class="metric-sub">{{ signalMode }}</div>
          </div>
        </div>
      </el-col>

      <el-col :xs="12" :sm="6" :md="6" :lg="3">
        <div class="metric-card resonance-card" :class="{ active: hasResonance }">
          <div class="metric-icon">
            <el-icon :size="28"><Connection /></el-icon>
          </div>
          <div class="metric-content">
            <div class="metric-label">共振信号</div>
            <div class="metric-value">{{ resonanceType }}</div>
            <div class="metric-sub">{{ resonanceScore }}分</div>
          </div>
        </div>
      </el-col>

      <el-col :xs="12" :sm="6" :md="6" :lg="3">
        <div class="metric-card ladder-card">
          <div class="metric-icon text-orange">
            <el-icon :size="28"><Trophy /></el-icon>
          </div>
          <div class="metric-content">
            <div class="metric-label">连板高度</div>
            <div class="metric-value">{{ maxHeight }}板</div>
            <div class="metric-sub">{{ ladderInfo }}</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="16" class="chart-section">
      <el-col :xs="24" :lg="16">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>📈 情绪走势（近7日）</span>
              <el-button-group size="small">
                <el-button :type="chartRange === 7 ? 'primary' : ''" @click="chartRange = 7">7日</el-button>
                <el-button :type="chartRange === 14 ? 'primary' : ''" @click="chartRange = 14">14日</el-button>
                <el-button :type="chartRange === 30 ? 'primary' : ''" @click="chartRange = 30">30日</el-button>
              </el-button-group>
            </div>
          </template>
          <EmotionTrendChart
            :data="emotionTrendData"
            :range="chartRange"
            height="300px"
          />
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="8">
        <el-card class="chart-card">
          <template #header>
            <span>🎯 连板梯队分布</span>
          </template>
          <LadderPieChart
            :data="ladderData"
            height="300px"
          />
        </el-card>
      </el-col>
    </el-row>

    <!-- 信号和热点 -->
    <el-row :gutter="16" class="signal-section">
      <el-col :xs="24" :md="12">
        <el-card class="signal-card-list">
          <template #header>
            <div class="card-header">
              <span>🚀 今日买入信号</span>
              <el-tag :type="signalModeType" size="small">{{ signalMode }}</el-tag>
            </div>
          </template>
          <div v-if="buySignals.length === 0" class="empty-signal">
            暂无信号，等待市场机会
          </div>
          <div v-else class="signal-list">
            <div
              v-for="signal in buySignals"
              :key="signal.code"
              class="signal-item"
              @click="$emit('view-stock', signal)"
            >
              <div class="signal-stock">
                <span class="stock-name">{{ signal.name }}</span>
                <span class="stock-code">{{ signal.code }}</span>
              </div>
              <div class="signal-info">
                <el-tag size="small" :type="getSignalTagType(signal.type)">
                  {{ signal.type === 'chase_high' ? '追高' : '低吸' }}
                </el-tag>
                <span class="signal-score">{{ signal.score }}分</span>
              </div>
              <div class="signal-price">
                入场价 ¥{{ signal.entry_price }}
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="12">
        <el-card class="hot-sector-card">
          <template #header>
            <span>🔥 热门板块</span>
          </template>
          <div class="sector-list">
            <div
              v-for="(sector, index) in hotSectors"
              :key="sector.name"
              class="sector-item"
            >
              <span class="sector-rank" :class="getRankClass(index)">{{ index + 1 }}</span>
              <span class="sector-name">{{ sector.name }}</span>
              <span class="sector-chg" :class="sector.pct_chg > 0 ? 'text-red' : 'text-green'">
                {{ sector.pct_chg > 0 ? '+' : '' }}{{ sector.pct_chg?.toFixed(2) }}%
              </span>
              <div class="sector-bar">
                <div
                  class="sector-bar-inner"
                  :class="sector.pct_chg > 0 ? 'bar-red' : 'bar-green'"
                  :style="{ width: Math.min(Math.abs(sector.pct_chg || 0) * 10, 100) + '%' }"
                ></div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 操作建议 -->
    <el-row :gutter="16" class="action-section">
      <el-col :span="24">
        <el-card class="action-card">
          <template #header>
            <span>📋 今日操作建议</span>
          </template>
          <div class="action-plan">
            <div class="plan-summary">
              {{ actionSummary }}
            </div>
            <div class="plan-actions">
              <div v-for="(action, index) in actionItems" :key="index" class="action-item">
                <el-icon class="action-icon"><CircleCheck /></el-icon>
                <span>{{ action }}</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import {
  Top, Bottom, TrendCharts, Wallet, Bell, Connection, Trophy, CircleCheck
} from '@element-plus/icons-vue'
import EmotionTrendChart from './EmotionTrendChart.vue'
import LadderPieChart from './LadderPieChart.vue'

const props = defineProps({
  analysisData: { type: Object, default: () => ({}) },
  eastmoneyData: { type: Object, default: () => ({}) },
  kaipanlaData: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['view-stock', 'refresh'])

const chartRange = ref(7)
const emotionHistory = ref([])

// 获取情绪历史数据
const fetchEmotionHistory = async () => {
  try {
    const res = await fetch(`/api/emotion/history?days=${chartRange.value}`)
    const data = await res.json()
    if (data.code === 0 && data.data?.history) {
      emotionHistory.value = data.data.history
    }
  } catch (err) {
    console.error('获取情绪历史失败:', err)
  }
}

// 组件挂载时获取历史数据
onMounted(() => {
  fetchEmotionHistory()
})

// 当 eastmoneyData 更新时（爬虫完成），刷新历史数据
watch(() => props.eastmoneyData?.date, (newDate) => {
  if (newDate) {
    // 延迟 500ms 确保后端已保存
    setTimeout(fetchEmotionHistory, 500)
  }
})

// 情绪周期 - 从 market_analysis.emotion 获取
const emotionPhase = computed(() => {
  const phases = {
    'high_tide': '高潮期',
    'warming': '回暖期',
    'repair': '修复期',
    'ebb_tide': '退潮期',
    'ice_point': '冰点期'
  }
  const phase = props.analysisData?.market_analysis?.emotion?.phase
  return phases[phase] || '未知'
})

const emotionScore = computed(() => props.analysisData?.market_analysis?.emotion?.score || 0)

const phaseEmoji = computed(() => {
  const emojis = {
    'high_tide': '🔥',
    'warming': '🌱',
    'repair': '🔧',
    'ebb_tide': '📉',
    'ice_point': '❄️'
  }
  const phase = props.analysisData?.market_analysis?.emotion?.phase
  return emojis[phase] || '❓'
})

const emotionPhaseClass = computed(() => {
  const phase = props.analysisData?.market_analysis?.emotion?.phase || 'unknown'
  return `phase-${phase}`
})

// 涨跌停数据
const limitUpCount = computed(() => {
  return props.kaipanlaData?.limit_up?.count ||
         props.eastmoneyData?.limit_up_down?.limit_up_count || 0
})

const limitDownCount = computed(() => {
  return props.kaipanlaData?.limit_down?.count ||
         props.eastmoneyData?.limit_up_down?.limit_down_count || 0
})

const continuousCount = computed(() => {
  return props.kaipanlaData?.continuous_ladder?.statistics?.total_continuous || 0
})

const brokenRate = computed(() => {
  const broken = props.kaipanlaData?.broken_board?.count || 0
  const total = limitUpCount.value + broken
  return total > 0 ? Math.round(broken / total * 100) : 0
})

// 北向资金
const northFlow = computed(() => props.eastmoneyData?.north_flow?.total || 0)
const northFlow5d = computed(() => props.eastmoneyData?.north_flow?.avg_5d || 0)
const northFlowText = computed(() => {
  const flow = northFlow.value
  return (flow > 0 ? '+' : '') + flow.toFixed(1) + '亿'
})
const northFlowClass = computed(() => northFlow.value > 0 ? 'text-red' : 'text-green')

// 仓位建议
const maxPosition = computed(() => props.analysisData?.position_advice?.max_position || 50)
const singlePosition = computed(() => props.analysisData?.position_advice?.single_position || 10)

// 信号
const buySignals = computed(() => props.analysisData?.buy_signals?.signals || [])
const signalCount = computed(() => buySignals.value.length)
const signalMode = computed(() => {
  const modes = {
    'chase_high': '追高模式',
    'chase_high_cautious': '谨慎追高',
    'low_buy': '低吸模式',
    'wait': '观望等待'
  }
  return modes[props.analysisData?.buy_signals?.mode] || '观望'
})
const signalModeType = computed(() => {
  const mode = props.analysisData?.buy_signals?.mode
  if (mode === 'chase_high') return 'danger'
  if (mode === 'low_buy') return 'success'
  return 'info'
})

// 共振 - 从 market_analysis.resonance 获取
const hasResonance = computed(() => props.analysisData?.market_analysis?.resonance?.is_resonance || false)
const resonanceType = computed(() => props.analysisData?.market_analysis?.resonance?.type || '无共振')
const resonanceScore = computed(() => props.analysisData?.market_analysis?.resonance?.score || 0)

// 连板梯队 - 优先使用开盘啦数据，备用东财数据
const maxHeight = computed(() => {
  // 优先开盘啦
  if (props.kaipanlaData?.continuous_ladder?.max_height) {
    return props.kaipanlaData.continuous_ladder.max_height
  }
  // 备用：从东财涨停股计算
  const limitUpList = props.eastmoneyData?.limit_up_down?.limit_up || []
  return limitUpList.reduce((max, s) => Math.max(max, s.continuous || 0), 0)
})

const ladderInfo = computed(() => {
  const dist = getLadderDistribution()
  const parts = []
  if (dist['2板']) parts.push(`2板${dist['2板']}只`)
  if (dist['3板']) parts.push(`3板${dist['3板']}只`)
  if (dist['4板']) parts.push(`4板${dist['4板']}只`)
  return parts.join(' ') || '暂无连板'
})

// 获取连板分布数据
const getLadderDistribution = () => {
  // 优先开盘啦
  if (props.kaipanlaData?.continuous_ladder?.statistics?.height_distribution) {
    return props.kaipanlaData.continuous_ladder.statistics.height_distribution
  }
  // 备用：从东财 emotion_cycle.continuous_stats 获取
  if (props.eastmoneyData?.emotion_cycle?.continuous_stats) {
    return props.eastmoneyData.emotion_cycle.continuous_stats
  }
  // 备用：从东财涨停股统计
  const limitUpList = props.eastmoneyData?.limit_up_down?.limit_up || []
  const dist = {}
  limitUpList.forEach(s => {
    const key = `${s.continuous || 1}板`
    dist[key] = (dist[key] || 0) + 1
  })
  return dist
}

const ladderData = computed(() => {
  const dist = getLadderDistribution()
  return Object.entries(dist).map(([name, value]) => ({ name, value }))
})

// 热门板块
const hotSectors = computed(() => {
  const sectors = props.eastmoneyData?.sector_flow || []
  return sectors.slice(0, 8)
})

// 图表数据 - 情绪走势
const emotionTrendData = computed(() => {
  // 优先使用从API获取的历史数据
  if (emotionHistory.value.length > 0) {
    return emotionHistory.value
  }
  // 兼容：如果props中有历史数据
  if (props.eastmoneyData?.emotion_history?.length > 0) {
    return props.eastmoneyData.emotion_history
  }
  // 如果有当日数据，至少显示一个点
  const todayEmotion = props.eastmoneyData?.emotion_cycle
  if (todayEmotion) {
    const today = new Date()
    return [{
      date: today.toISOString().split('T')[0],
      score: todayEmotion.score || todayEmotion.cycle_score || 0,
      phase: todayEmotion.phase || todayEmotion.cycle_phase || '未知',
      limit_up: todayEmotion.limit_up_count || 0
    }]
  }
  return []
})

// 操作建议
const actionSummary = computed(() => props.analysisData?.action_plan?.summary || '等待数据加载...')
const actionItems = computed(() => props.analysisData?.action_plan?.actions || [])

// 辅助方法
const getSignalTagType = (type) => {
  return type === 'chase_high' ? 'danger' : 'success'
}

const getRankClass = (index) => {
  if (index === 0) return 'rank-1'
  if (index === 1) return 'rank-2'
  if (index === 2) return 'rank-3'
  return ''
}
</script>

<style scoped>
.dashboard-view {
  padding: 16px;
  background: #f5f7fa;
  min-height: 100vh;
}

/* 指标卡片 */
.metric-cards {
  margin-bottom: 16px;
}

.metric-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  transition: all 0.3s;
  margin-bottom: 16px;
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.metric-icon {
  width: 50px;
  height: 50px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
}

.phase-emoji {
  font-size: 28px;
}

.metric-content {
  flex: 1;
}

.metric-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.metric-value {
  font-size: 20px;
  font-weight: 700;
  color: #303133;
}

.metric-score, .metric-sub {
  font-size: 12px;
  color: #909399;
}

/* 情绪周期卡片颜色 */
.phase-high_tide { border-left: 4px solid #f56c6c; }
.phase-high_tide .metric-icon { background: #fef0f0; color: #f56c6c; }

.phase-warming { border-left: 4px solid #67c23a; }
.phase-warming .metric-icon { background: #f0f9eb; color: #67c23a; }

.phase-repair { border-left: 4px solid #e6a23c; }
.phase-repair .metric-icon { background: #fdf6ec; color: #e6a23c; }

.phase-ebb_tide { border-left: 4px solid #909399; }
.phase-ebb_tide .metric-icon { background: #f4f4f5; color: #909399; }

.phase-ice_point { border-left: 4px solid #409eff; }
.phase-ice_point .metric-icon { background: #ecf5ff; color: #409eff; }

/* 共振卡片激活 */
.resonance-card.active {
  border-left: 4px solid #e6a23c;
  background: linear-gradient(135deg, #fff 0%, #fdf6ec 100%);
}

/* 图表区域 */
.chart-section {
  margin-bottom: 16px;
}

.chart-card {
  border-radius: 12px;
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* 信号列表 */
.signal-section {
  margin-bottom: 16px;
}

.signal-card-list, .hot-sector-card {
  border-radius: 12px;
  height: 100%;
}

.empty-signal {
  text-align: center;
  padding: 40px;
  color: #909399;
}

.signal-list {
  max-height: 300px;
  overflow-y: auto;
}

.signal-item {
  display: flex;
  align-items: center;
  padding: 12px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  transition: background 0.2s;
}

.signal-item:hover {
  background: #f5f7fa;
}

.signal-item:last-child {
  border-bottom: none;
}

.signal-stock {
  flex: 1;
}

.stock-name {
  font-weight: 600;
  margin-right: 8px;
}

.stock-code {
  font-size: 12px;
  color: #909399;
}

.signal-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-right: 16px;
}

.signal-score {
  font-weight: 600;
  color: #e6a23c;
}

.signal-price {
  font-size: 12px;
  color: #606266;
}

/* 板块列表 */
.sector-list {
  max-height: 300px;
  overflow-y: auto;
}

.sector-item {
  display: flex;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #f0f0f0;
}

.sector-item:last-child {
  border-bottom: none;
}

.sector-rank {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  background: #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  margin-right: 12px;
}

.rank-1 { background: #ffd700; color: #fff; }
.rank-2 { background: #c0c0c0; color: #fff; }
.rank-3 { background: #cd7f32; color: #fff; }

.sector-name {
  flex: 1;
  font-size: 14px;
}

.sector-chg {
  width: 60px;
  text-align: right;
  font-weight: 600;
  margin-right: 12px;
}

.sector-bar {
  width: 80px;
  height: 6px;
  background: #f0f0f0;
  border-radius: 3px;
  overflow: hidden;
}

.sector-bar-inner {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s;
}

.bar-red { background: linear-gradient(90deg, #f56c6c, #ff8080); }
.bar-green { background: linear-gradient(90deg, #67c23a, #85ce61); }

/* 操作建议 */
.action-card {
  border-radius: 12px;
}

.action-plan {
  padding: 8px 0;
}

.plan-summary {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 16px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;
}

.plan-actions {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 12px;
}

.action-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #fafafa;
  border-radius: 8px;
}

.action-icon {
  color: #67c23a;
}

/* 颜色 */
.text-red { color: #f56c6c; }
.text-green { color: #67c23a; }
.text-warning { color: #e6a23c; }
.text-orange { color: #ff9900; }

/* 响应式 */
@media (max-width: 768px) {
  .dashboard-view {
    padding: 12px;
  }

  .metric-card {
    padding: 12px;
  }

  .metric-value {
    font-size: 18px;
  }

  .plan-actions {
    grid-template-columns: 1fr;
  }
}
</style>
