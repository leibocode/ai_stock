<template>
  <div class="app-container" :class="{ 'blue-theme': useBlueUp }">
    <el-container>
      <!-- 新版简洁头部 -->
      <el-header class="app-header">
        <div class="header-left">
          <h1 class="app-title">🎯 情绪周期交易助手</h1>
          <div class="market-quick-info" v-if="eastmoneyData">
            <span class="info-item">
              <span class="info-label">情绪</span>
              <span class="info-value" :class="getEmotionClass">
                {{ eastmoneyData.market_emotion?.emotion_level || '修复期' }}
              </span>
            </span>
            <span class="info-divider">|</span>
            <span class="info-item">
              <span class="info-label">涨停</span>
              <span class="info-value up">{{ eastmoneyData.limit_up_down?.limit_up_count || 0 }}</span>
            </span>
            <span class="info-divider">|</span>
            <span class="info-item">
              <span class="info-label">北向</span>
              <span class="info-value" :class="(eastmoneyData.north_flow?.total || 0) >= 0 ? 'up' : 'down'">
                {{ (eastmoneyData.north_flow?.total || 0) >= 0 ? '+' : '' }}{{ eastmoneyData.north_flow?.total || 0 }}亿
              </span>
            </span>
          </div>
        </div>
        <div class="header-right">
          <el-date-picker
            v-model="currentDate"
            type="date"
            placeholder="交易日"
            format="MM-DD"
            value-format="YYYYMMDD"
            :disabled-date="disabledDate"
            @change="loadData"
            size="small"
            style="width: 100px"
          />
          <el-button size="small" @click="crawlData" :loading="crawling">
            刷新数据
          </el-button>
          <el-button size="small" @click="showSettingsDrawer = true">
            <el-icon><Setting /></el-icon>
          </el-button>
        </div>
      </el-header>

      <el-main class="app-main">
        <!-- 核心功能导航 -->
        <div class="core-nav">
          <div
            v-for="nav in coreNavItems"
            :key="nav.name"
            class="nav-item"
            :class="{ active: activeTab === nav.name }"
            @click="activeTab = nav.name"
          >
            <span class="nav-icon">{{ nav.icon }}</span>
            <span class="nav-label">{{ nav.label }}</span>
          </div>
          <div class="nav-item more-btn" @click="showAnalysisDrawer = true">
            <span class="nav-icon">📊</span>
            <span class="nav-label">更多分析</span>
            <el-icon class="arrow-icon"><ArrowRight /></el-icon>
          </div>
        </div>

        <!-- 核心功能内容区 -->
        <div class="core-content">
          <!-- 今日决策 -->
          <TodayDecision
            v-if="activeTab === 'decision'"
            :emotion-phase="kaipanlaData?.emotion_phase || eastmoneyData?.market_emotion?.emotion_phase || 'repair'"
            :emotion-score="kaipanlaData?.emotion_score || eastmoneyData?.market_emotion?.emotion_score || 50"
            :market-data="eastmoneyData"
            :kaipanla-data="kaipanlaData"
            @navigate="navigateToTab"
          />

          <!-- 我的持仓 -->
          <MyHoldings
            v-if="activeTab === 'holdings'"
            :emotion-phase="kaipanlaData?.emotion_phase || eastmoneyData?.market_emotion?.emotion_phase || 'repair'"
            :emotion-score="kaipanlaData?.emotion_score || eastmoneyData?.market_emotion?.emotion_score || 50"
          />

          <!-- 智能选股 -->
          <SmartPicks
            v-if="activeTab === 'picks'"
            :emotion-phase="kaipanlaData?.emotion_phase || eastmoneyData?.market_emotion?.emotion_phase || 'repair'"
            :emotion-score="kaipanlaData?.emotion_score || eastmoneyData?.market_emotion?.emotion_score || 50"
            @add-to-holdings="addToHoldings"
            @view-detail="openChanDetail"
          />

          <!-- 预警中心 -->
          <AlertCenter
            v-if="activeTab === 'alerts'"
            :emotion-phase="kaipanlaData?.emotion_phase || eastmoneyData?.market_emotion?.emotion_phase || 'repair'"
          />

          <!-- 二级分析功能（从抽屉打开后显示在主区域） -->
          <DashboardView
            v-if="activeTab === 'dashboard'"
            :analysis-data="analysisData"
            :eastmoney-data="eastmoneyData"
            :kaipanla-data="kaipanlaData"
            @view-stock="openChanDetail"
            @refresh="crawlData"
          />

          <!-- 量价分析内容 -->
          <div v-if="activeTab === 'volume'" class="analysis-content">
            <el-row :gutter="20">
              <el-col :span="12">
                <el-card>
                  <template #header>💰 成交额TOP50</template>
                  <el-table :data="eastmoneyData?.volume_analysis?.volume_top || volumeTop" height="350" stripe size="small">
                    <el-table-column prop="code" label="代码" width="70" />
                    <el-table-column prop="name" label="名称" width="70" />
                    <el-table-column prop="amount" label="成交额(亿)" width="80" />
                    <el-table-column prop="turnover" label="换手%" width="60" />
                    <el-table-column prop="pct_chg" label="涨跌" width="60">
                      <template #default="{ row }">
                        <span :class="row.pct_chg >= 0 ? 'text-red' : 'text-green'">{{ row.pct_chg }}%</span>
                      </template>
                    </el-table-column>
                  </el-table>
                </el-card>
              </el-col>
              <el-col :span="12">
                <el-card>
                  <template #header>🚀 底部放量 (量比>3, 位置&lt;30%)</template>
                  <el-table :data="eastmoneyData?.volume_analysis?.bottom_volume || bottomVolume" height="350" stripe size="small">
                    <el-table-column prop="code" label="代码" width="70" />
                    <el-table-column prop="name" label="名称" width="70" />
                    <el-table-column prop="volume_ratio" label="量比" width="60" />
                    <el-table-column prop="position" label="位置%" width="60" />
                    <el-table-column prop="pct_chg" label="涨幅" width="60">
                      <template #default="{ row }"><span class="text-red">{{ row.pct_chg }}%</span></template>
                    </el-table-column>
                    <el-table-column prop="amount" label="成交额" width="60" />
                  </el-table>
                </el-card>
              </el-col>
            </el-row>
            <el-row :gutter="20" style="margin-top: 15px">
              <el-col :span="12">
                <el-card>
                  <template #header>🎯 多因子选股TOP (综合得分)</template>
                  <el-table :data="eastmoneyData?.multi_factor?.stocks?.slice(0, 20) || []" height="300" stripe size="small">
                    <el-table-column prop="code" label="代码" width="70" />
                    <el-table-column prop="name" label="名称" width="70" />
                    <el-table-column prop="score" label="总分" width="50">
                      <template #default="{ row }">
                        <b class="text-red">{{ row.score }}</b>
                      </template>
                    </el-table-column>
                    <el-table-column prop="pct_chg" label="涨幅" width="55">
                      <template #default="{ row }">
                        <span class="text-red">{{ row.pct_chg }}%</span>
                      </template>
                    </el-table-column>
                    <el-table-column label="因子明细" width="120">
                      <template #default="{ row }">
                        <span style="font-size: 10px; color: #909399;">
                          涨{{ row.factors?.['涨幅'] || 0 }} 强{{ row.factors?.['相对强度'] || 0 }}
                          板{{ row.factors?.['板块'] || 0 }} 量{{ row.factors?.['量比'] || 0 }}
                        </span>
                      </template>
                    </el-table-column>
                  </el-table>
                </el-card>
              </el-col>
              <el-col :span="12">
                <el-card>
                  <template #header>
                    💪 逆势上涨 (板块>大盘, 个股>板块)
                    <span style="font-weight: normal; font-size: 12px; color: #909399; margin-left: 8px;">
                      大盘: {{ eastmoneyData?.sector_strength?.market_chg || 0 }}%
                    </span>
                  </template>
                  <el-table :data="eastmoneyData?.sector_strength?.counter_trend || counterTrend" height="300" stripe size="small">
                    <el-table-column prop="code" label="代码" width="70" />
                    <el-table-column prop="name" label="名称" width="70" />
                    <el-table-column prop="sector" label="板块" width="70" />
                    <el-table-column prop="pct_chg" label="涨幅" width="55">
                      <template #default="{ row }"><span class="text-red">{{ row.pct_chg }}%</span></template>
                    </el-table-column>
                    <el-table-column prop="sector_chg" label="板块" width="55">
                      <template #default="{ row }">
                        <span :class="row.sector_chg >= 0 ? 'text-red' : 'text-green'">{{ row.sector_chg }}%</span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="strength" label="强度" width="50">
                      <template #default="{ row }"><b class="text-red">{{ row.strength }}</b></template>
                    </el-table-column>
                  </el-table>
                </el-card>
              </el-col>
            </el-row>
            <el-row :gutter="20" style="margin-top: 15px">
              <el-col :span="12">
                <el-card>
                  <template #header>🔥 共振板块龙头 (板块与大盘同向)</template>
                  <el-table :data="eastmoneyData?.sector_strength?.sector_leaders || []" height="300" stripe size="small">
                    <el-table-column prop="code" label="代码" width="70" />
                    <el-table-column prop="name" label="名称" width="70" />
                    <el-table-column prop="sector" label="板块" width="70" />
                    <el-table-column prop="pct_chg" label="涨幅" width="55">
                      <template #default="{ row }"><span class="text-red">{{ row.pct_chg }}%</span></template>
                    </el-table-column>
                    <el-table-column prop="amount" label="成交额" width="55">
                      <template #default="{ row }">{{ row.amount }}亿</template>
                    </el-table-column>
                  </el-table>
                </el-card>
              </el-col>
              <el-col :span="12">
                <el-card>
                  <template #header>📊 共振板块统计</template>
                  <div style="max-height: 300px; overflow-y: auto;">
                    <div v-for="sector in eastmoneyData?.sector_strength?.resonance_sectors || []" :key="sector.code" class="resonance-sector">
                      <div class="sector-header">
                        <span class="sector-name">{{ sector.name }}</span>
                        <span class="sector-chg text-red">{{ sector.pct_chg }}%</span>
                        <span class="sector-strength">强度: {{ sector.strength }}</span>
                      </div>
                      <div class="sector-leaders">
                        <span v-for="leader in sector.leaders" :key="leader.code" class="leader-tag">
                          {{ leader.name }} <span class="text-red">{{ leader.pct_chg }}%</span>
                        </span>
                      </div>
                    </div>
                  </div>
                </el-card>
              </el-col>
            </el-row>
          </div>

          <!-- 技术指标 -->
          <div v-if="activeTab === 'indicator'" class="analysis-content">
            <el-row :gutter="20">
              <el-col :span="12">
                <el-card>
                  <template #header>📉 RSI超卖反弹 (放量反弹)</template>
                  <el-table :data="eastmoneyData?.technical?.rsi_oversold || oversold" height="300" stripe size="small">
                    <el-table-column prop="code" label="代码" width="70" />
                    <el-table-column prop="name" label="名称" width="70" />
                    <el-table-column prop="pct_chg" label="涨幅" width="60">
                      <template #default="{ row }">
                        <span class="text-red">{{ row.pct_chg }}%</span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="turnover" label="换手%" width="60" />
                    <el-table-column prop="signal" label="信号" width="70" />
                  </el-table>
                </el-card>
              </el-col>
              <el-col :span="12">
                <el-card>
                  <template #header>📊 KDJ底部信号 (下影线反转)</template>
                  <el-table :data="eastmoneyData?.technical?.kdj_bottom || kdjBottom" height="300" stripe size="small">
                    <el-table-column prop="code" label="代码" width="70" />
                    <el-table-column prop="name" label="名称" width="70" />
                    <el-table-column prop="pct_chg" label="涨幅" width="60">
                      <template #default="{ row }">
                        <span class="text-red">{{ row.pct_chg }}%</span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="lower_shadow" label="下影%" width="60" />
                    <el-table-column prop="signal" label="信号" width="70" />
                  </el-table>
                </el-card>
              </el-col>
            </el-row>
            <el-row :gutter="20" style="margin-top: 15px">
              <el-col :span="12">
                <el-card>
                  <template #header>✨ MACD金叉信号 (放量上攻)</template>
                  <el-table :data="eastmoneyData?.technical?.macd_golden || macdGolden" height="300" stripe size="small">
                    <el-table-column prop="code" label="代码" width="70" />
                    <el-table-column prop="name" label="名称" width="70" />
                    <el-table-column prop="pct_chg" label="涨幅" width="60">
                      <template #default="{ row }">
                        <span class="text-red">{{ row.pct_chg }}%</span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="volume_ratio" label="量比" width="55" />
                    <el-table-column prop="signal" label="信号" width="70" />
                  </el-table>
                </el-card>
              </el-col>
              <el-col :span="12">
                <el-card>
                  <template #header>🎯 突破形态 (放量创新高)</template>
                  <el-table :data="eastmoneyData?.technical?.breakout || breakout" height="300" stripe size="small">
                    <el-table-column prop="code" label="代码" width="70" />
                    <el-table-column prop="name" label="名称" width="70" />
                    <el-table-column prop="pct_chg" label="涨幅" width="60">
                      <template #default="{ row }">
                        <span class="text-red">{{ row.pct_chg }}%</span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="volume_ratio" label="量比" width="55" />
                    <el-table-column prop="type" label="类型" width="70" />
                  </el-table>
                </el-card>
              </el-col>
            </el-row>
          </div>

          <!-- 缠论选股 -->
          <div v-if="activeTab === 'chan'" class="analysis-content">
            <div style="margin-bottom: 15px; display: flex; gap: 10px; align-items: center;">
              <el-button type="primary" @click="calcChanIndicators" :loading="chanCalcing">
                计算缠论指标
              </el-button>
              <el-button @click="loadChanData">刷新数据</el-button>
              <span style="color: #909399; font-size: 12px;">
                提示：需先计算缠论指标才能显示选股结果
              </span>
            </div>
            <el-row :gutter="20">
              <el-col :span="8">
                <el-card>
                  <template #header>📈 一买信号 ({{ chanFirstBuy.length }})</template>
                  <el-table :data="chanFirstBuy" height="280" stripe size="small">
                    <el-table-column prop="ts_code" label="代码" width="90">
                      <template #default="{ row }">
                        <el-link type="primary" @click="openChanDetail(row)">{{ row.ts_code }}</el-link>
                      </template>
                    </el-table-column>
                    <el-table-column prop="name" label="名称" width="70" />
                    <el-table-column prop="industry" label="行业" width="70" />
                    <el-table-column prop="price" label="价格" width="60" />
                  </el-table>
                </el-card>
              </el-col>
              <el-col :span="8">
                <el-card>
                  <template #header>📊 二买信号 ({{ chanSecondBuy.length }})</template>
                  <el-table :data="chanSecondBuy" height="280" stripe size="small">
                    <el-table-column prop="ts_code" label="代码" width="90">
                      <template #default="{ row }">
                        <el-link type="primary" @click="openChanDetail(row)">{{ row.ts_code }}</el-link>
                      </template>
                    </el-table-column>
                    <el-table-column prop="name" label="名称" width="70" />
                    <el-table-column prop="industry" label="行业" width="70" />
                    <el-table-column prop="price" label="价格" width="60" />
                  </el-table>
                </el-card>
              </el-col>
              <el-col :span="8">
                <el-card>
                  <template #header>🚀 三买信号 ({{ chanThirdBuy.length }})</template>
                  <el-table :data="chanThirdBuy" height="280" stripe size="small">
                    <el-table-column prop="ts_code" label="代码" width="90">
                      <template #default="{ row }">
                        <el-link type="primary" @click="openChanDetail(row)">{{ row.ts_code }}</el-link>
                      </template>
                    </el-table-column>
                    <el-table-column prop="name" label="名称" width="70" />
                    <el-table-column prop="industry" label="行业" width="70" />
                    <el-table-column prop="price" label="价格" width="60" />
                  </el-table>
                </el-card>
              </el-col>
            </el-row>
            <el-row :gutter="20" style="margin-top: 15px">
              <el-col :span="8">
                <el-card>
                  <template #header>⬇️ 底背驰 ({{ chanBottomDiverge.length }})</template>
                  <el-table :data="chanBottomDiverge" height="280" stripe size="small">
                    <el-table-column prop="ts_code" label="代码" width="90">
                      <template #default="{ row }">
                        <el-link type="primary" @click="openChanDetail(row)">{{ row.ts_code }}</el-link>
                      </template>
                    </el-table-column>
                    <el-table-column prop="name" label="名称" width="70" />
                    <el-table-column prop="industry" label="行业" width="70" />
                    <el-table-column prop="bi_low" label="笔低点" width="60" />
                  </el-table>
                </el-card>
              </el-col>
              <el-col :span="8">
                <el-card>
                  <template #header>⬆️ 顶背驰 ({{ chanTopDiverge.length }})</template>
                  <el-table :data="chanTopDiverge" height="280" stripe size="small">
                    <el-table-column prop="ts_code" label="代码" width="90">
                      <template #default="{ row }">
                        <el-link type="primary" @click="openChanDetail(row)">{{ row.ts_code }}</el-link>
                      </template>
                    </el-table-column>
                    <el-table-column prop="name" label="名称" width="70" />
                    <el-table-column prop="industry" label="行业" width="70" />
                    <el-table-column prop="bi_high" label="笔高点" width="60" />
                  </el-table>
                </el-card>
              </el-col>
              <el-col :span="8">
                <el-card>
                  <template #header>🔄 中枢震荡 ({{ chanHubShake.length }})</template>
                  <el-table :data="chanHubShake" height="280" stripe size="small">
                    <el-table-column prop="ts_code" label="代码" width="90">
                      <template #default="{ row }">
                        <el-link type="primary" @click="openChanDetail(row)">{{ row.ts_code }}</el-link>
                      </template>
                    </el-table-column>
                    <el-table-column prop="name" label="名称" width="70" />
                    <el-table-column prop="position" label="位置%" width="60">
                      <template #default="{ row }">
                        <span :class="row.position > 50 ? 'text-red' : 'text-green'">{{ row.position }}%</span>
                      </template>
                    </el-table-column>
                  </el-table>
                </el-card>
              </el-col>
            </el-row>
          </div>

          <!-- 板块资金 -->
          <div v-if="activeTab === 'money'" class="analysis-content">
            <el-row :gutter="20">
              <el-col :span="12">
                <el-card>
                  <template #header>💰 板块资金流向TOP</template>
                  <el-table :data="eastmoneyData?.sector_flow || industryHot" height="350" stripe size="small">
                    <el-table-column prop="name" label="板块" width="90" />
                    <el-table-column prop="pct_chg" label="涨跌" width="60">
                      <template #default="{ row }">
                        <span :class="row.pct_chg >= 0 ? 'text-red' : 'text-green'">{{ row.pct_chg }}%</span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="main_net" label="主力净(亿)" width="80">
                      <template #default="{ row }">
                        <span :class="row.main_net >= 0 ? 'text-red' : 'text-green'">{{ row.main_net }}</span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="main_pct" label="占比%" width="60" />
                  </el-table>
                </el-card>
              </el-col>
              <el-col :span="12">
                <el-card>
                  <template #header>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                      <span>🐉 龙虎榜</span>
                      <el-button size="small" type="primary" link @click="window.open(`https://data.eastmoney.com/stock/tradedetail.html`, '_blank')">
                        查看详情 →
                      </el-button>
                    </div>
                  </template>
                  <el-table :data="eastmoneyData?.dragon_tiger || dragonTiger" height="350" stripe size="small">
                    <el-table-column prop="code" label="代码" width="70" />
                    <el-table-column prop="name" label="名称" width="70" />
                    <el-table-column prop="pct_chg" label="涨跌" width="60">
                      <template #default="{ row }">
                        <span :class="row.pct_chg >= 0 ? 'text-red' : 'text-green'">{{ row.pct_chg }}%</span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="net_amount" label="净买入" width="70">
                      <template #default="{ row }">
                        <span :class="row.net_amount >= 0 ? 'text-red' : 'text-green'">{{ row.net_amount }}万</span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="reason" label="原因" />
                  </el-table>
                </el-card>
              </el-col>
            </el-row>
            <el-row :gutter="20" style="margin-top: 15px">
              <el-col :span="12">
                <el-card>
                  <template #header>
                    📈 北向资金 ({{ eastmoneyData?.north_flow?.total || 0 }}亿)
                  </template>
                  <div style="padding: 10px 0; font-size: 13px;">
                    沪股通: <b :class="(eastmoneyData?.north_flow?.hk_to_sh || 0) >= 0 ? 'text-red' : 'text-green'">
                      {{ eastmoneyData?.north_flow?.hk_to_sh || 0 }}亿
                    </b>
                    &nbsp;&nbsp;
                    深股通: <b :class="(eastmoneyData?.north_flow?.hk_to_sz || 0) >= 0 ? 'text-red' : 'text-green'">
                      {{ eastmoneyData?.north_flow?.hk_to_sz || 0 }}亿
                    </b>
                  </div>
                  <el-table :data="eastmoneyData?.north_flow?.top_holdings || northBuy" height="230" stripe size="small">
                    <el-table-column prop="code" label="代码" width="70" />
                    <el-table-column prop="name" label="名称" width="80" />
                    <el-table-column prop="hold_market_cap" label="持仓(亿)" width="80" />
                    <el-table-column prop="hold_ratio" label="占比%" width="60" />
                  </el-table>
                </el-card>
              </el-col>
              <el-col :span="12">
                <el-card>
                  <template #header>💳 融资买入TOP</template>
                  <el-table :data="marginBuy" height="300" stripe size="small">
                    <el-table-column prop="ts_code" label="代码" width="90" />
                    <el-table-column prop="name" label="名称" width="70" />
                    <el-table-column prop="industry" label="行业" width="70" />
                    <el-table-column prop="rz_buy" label="融资买入(万)" width="100" />
                    <el-table-column prop="rz_balance" label="余额(亿)" width="80" />
                  </el-table>
                </el-card>
              </el-col>
            </el-row>
          </div>

          <!-- 涨跌停 -->
          <div v-if="activeTab === 'limit'" class="analysis-content">
            <el-row :gutter="20">
              <el-col :span="12">
                <el-card>
                  <template #header>
                    🔴 涨停股 ({{ eastmoneyData?.limit_up_down?.limit_up_count || 0 }})
                  </template>
                  <el-table :data="eastmoneyData?.limit_up_down?.limit_up || limitUpList" height="400" stripe size="small">
                    <el-table-column prop="code" label="代码" width="70" />
                    <el-table-column prop="name" label="名称" width="70" />
                    <el-table-column prop="reason" label="涨停原因" width="100" />
                    <el-table-column prop="first_time" label="首封" width="55" />
                    <el-table-column prop="open_times" label="开板" width="45" />
                    <el-table-column prop="continuous" label="连板" width="45">
                      <template #default="{ row }">
                        <span v-if="row.continuous > 1" class="text-red">{{ row.continuous }}</span>
                        <span v-else>{{ row.continuous }}</span>
                      </template>
                    </el-table-column>
                  </el-table>
                </el-card>
              </el-col>
              <el-col :span="12">
                <el-card>
                  <template #header>
                    🟢 跌停股 ({{ eastmoneyData?.limit_up_down?.limit_down_count || 0 }})
                  </template>
                  <el-table :data="eastmoneyData?.limit_up_down?.limit_down || limitDownList" height="400" stripe size="small">
                    <el-table-column prop="code" label="代码" width="70" />
                    <el-table-column prop="name" label="名称" width="70" />
                    <el-table-column prop="pct_chg" label="跌幅" width="60">
                      <template #default="{ row }">
                        <span class="text-green">{{ row.pct_chg }}%</span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="amount" label="成交额(亿)" width="80" />
                  </el-table>
                </el-card>
              </el-col>
            </el-row>
          </div>

          <!-- 形态信号 -->
          <div v-if="activeTab === 'pattern'" class="analysis-content">
            <el-row :gutter="20">
              <el-col :span="12">
                <el-card>
                  <template #header>🔻 顶部放量 (高位出货信号)</template>
                  <el-table :data="eastmoneyData?.volume_analysis?.top_volume || topVolume" height="300" stripe size="small">
                    <el-table-column prop="code" label="代码" width="70" />
                    <el-table-column prop="name" label="名称" width="70" />
                    <el-table-column prop="volume_ratio" label="量比" width="60" />
                    <el-table-column prop="position" label="位置%" width="60" />
                    <el-table-column prop="pct_chg" label="涨跌" width="60">
                      <template #default="{ row }">
                        <span :class="row.pct_chg >= 0 ? 'text-red' : 'text-green'">{{ row.pct_chg }}%</span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="amount" label="成交额" width="60" />
                  </el-table>
                </el-card>
              </el-col>
              <el-col :span="12">
                <el-card>
                  <template #header>🌍 行业跳空</template>
                  <el-table :data="industryGap" height="300" stripe size="small">
                    <el-table-column prop="industry" label="行业" width="80" />
                    <el-table-column prop="direction" label="方向" width="60">
                      <template #default="{ row }">
                        <span :class="row.direction === '高开' ? 'text-red' : 'text-green'">{{ row.direction }}</span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="avg_gap" label="均缺口%" width="70">
                      <template #default="{ row }">
                        <span :class="row.avg_gap >= 0 ? 'text-red' : 'text-green'">{{ row.avg_gap }}%</span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="stock_count" label="数量" width="50" />
                    <el-table-column prop="top_stock" label="领涨股" width="80" />
                  </el-table>
                </el-card>
              </el-col>
            </el-row>
            <el-row :gutter="20" style="margin-top: 15px">
              <el-col :span="12">
                <el-card>
                  <template #header>⬆️ 跳空高开</template>
                  <el-table :data="gapUp" height="300" stripe size="small">
                    <el-table-column prop="ts_code" label="代码" width="90" />
                    <el-table-column prop="name" label="名称" width="70" />
                    <el-table-column prop="industry" label="行业" width="70" />
                    <el-table-column prop="gap" label="缺口%" width="60">
                      <template #default="{ row }"><span class="text-red">{{ row.gap }}%</span></template>
                    </el-table-column>
                    <el-table-column prop="pct_chg" label="涨幅" width="60">
                      <template #default="{ row }"><span class="text-red">{{ row.pct_chg }}%</span></template>
                    </el-table-column>
                  </el-table>
                </el-card>
              </el-col>
              <el-col :span="12">
                <el-card>
                  <template #header>⬇️ 跳空低开</template>
                  <el-table :data="gapDown" height="300" stripe size="small">
                    <el-table-column prop="ts_code" label="代码" width="90" />
                    <el-table-column prop="name" label="名称" width="70" />
                    <el-table-column prop="industry" label="行业" width="70" />
                    <el-table-column prop="gap" label="缺口%" width="60">
                      <template #default="{ row }"><span class="text-green">{{ row.gap }}%</span></template>
                    </el-table-column>
                    <el-table-column prop="pct_chg" label="跌幅" width="60">
                      <template #default="{ row }"><span class="text-green">{{ row.pct_chg }}%</span></template>
                    </el-table-column>
                  </el-table>
                </el-card>
              </el-col>
            </el-row>
          </div>

          <!-- 东方财富数据 -->
          <div v-if="activeTab === 'eastmoney'" class="analysis-content">
            <div v-if="!eastmoneyData" style="text-align: center; padding: 50px; color: #909399;">
              点击"刷新数据"按钮获取数据
            </div>
            <template v-else>
              <!-- 非交易日提示 -->
              <div v-if="isNonTradingDay" class="non-trading-notice">
                ⚠️ 当前为非交易日，部分实时数据不可用。请选择历史交易日查看数据。
              </div>

              <!-- 情绪周期仪表盘 -->
              <div class="cycle-dashboard" v-if="eastmoneyData.emotion_cycle">
                <div class="cycle-main">
                  <div class="cycle-phase" :class="getCycleClass(eastmoneyData.emotion_cycle.cycle_phase)">
                    {{ eastmoneyData.emotion_cycle.cycle_phase }}
                  </div>
                  <div class="cycle-score">
                    得分: <b>{{ eastmoneyData.emotion_cycle.cycle_score }}</b>
                  </div>
                  <div class="cycle-desc">{{ eastmoneyData.emotion_cycle.phase_desc }}</div>
                  <div class="cycle-strategy">策略: {{ eastmoneyData.emotion_cycle.strategy }}</div>
                </div>
                <div class="cycle-indicators">
                  <div v-for="ind in eastmoneyData.emotion_cycle.indicators" :key="ind.name" class="indicator-item">
                    <span class="ind-name">{{ ind.name }}</span>
                    <span class="ind-value">{{ ind.value }}</span>
                    <span class="ind-score" :class="'score-' + ind.score">{{ ind.score }}</span>
                  </div>
                </div>
                <div class="cycle-chart">
                  <div class="chart-title">连板分布</div>
                  <div class="bar-chart">
                    <div v-for="(count, board) in eastmoneyData.emotion_cycle.continuous_stats" :key="board" class="bar-item">
                      <div class="bar" :style="{ height: Math.min(count * 3, 60) + 'px' }"></div>
                      <div class="bar-label">{{ board >= 5 ? '5+' : board }}板</div>
                      <div class="bar-value">{{ count }}</div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 策略看板 -->
              <div class="strategy-board" v-if="eastmoneyData.composite?.strategy">
                <div class="strategy-header">
                  <div class="strategy-title">
                    🎯 策略关注 - {{ eastmoneyData.composite.strategy.phase }}
                  </div>
                  <div class="strategy-desc">{{ eastmoneyData.composite.strategy.desc }}</div>
                </div>
                <div class="strategy-content">
                  <div class="strategy-tips">
                    <div class="tip-section">
                      <span class="tip-label">✅ 关注：</span>
                      <el-tooltip v-for="f in eastmoneyData.composite.strategy.focus" :key="f.text || f" :content="f.reason || ''" placement="top" :disabled="!f.reason">
                        <span class="tip-tag focus">{{ f.text || f }}</span>
                      </el-tooltip>
                    </div>
                    <div class="tip-section">
                      <span class="tip-label">❌ 回避：</span>
                      <el-tooltip v-for="a in eastmoneyData.composite.strategy.avoid" :key="a.text || a" :content="a.reason || ''" placement="top" :disabled="!a.reason">
                        <span class="tip-tag avoid">{{ a.text || a }}</span>
                      </el-tooltip>
                    </div>
                  </div>
                  <div class="strategy-stocks">
                    <div class="stock-label">推荐关注：</div>
                    <div class="stock-list">
                      <span v-for="s in eastmoneyData.composite.strategy.stocks?.slice(0, 8)" :key="s.code" class="stock-tag">
                        {{ s.name }}
                        <span class="text-red">{{ s.pct_chg }}%</span>
                        <span class="tag-reason">{{ s.reason }}</span>
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 多指标命中看板 -->
              <el-row :gutter="20" style="margin-bottom: 15px" v-if="eastmoneyData.composite?.top_hit?.length">
                <el-col :span="24">
                  <el-card>
                    <template #header>
                      <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span>🎯 多指标共振 (≥3个指标命中)</span>
                        <div class="indicator-stats">
                          <span v-for="(count, name) in eastmoneyData.composite.indicator_stats" :key="name" class="stat-tag" v-show="count > 0">
                            {{ name }}: {{ count }}
                          </span>
                        </div>
                      </div>
                    </template>
                    <el-table :data="eastmoneyData.composite.top_hit" height="250" stripe size="small">
                      <el-table-column prop="code" label="代码" width="70" />
                      <el-table-column prop="name" label="名称" width="70" />
                      <el-table-column prop="hit_count" label="命中" width="50">
                        <template #default="{ row }">
                          <b class="text-red">{{ row.hit_count }}</b>
                        </template>
                      </el-table-column>
                      <el-table-column prop="pct_chg" label="涨幅" width="60">
                        <template #default="{ row }">
                          <span :class="row.pct_chg >= 0 ? 'text-red' : 'text-green'">{{ row.pct_chg }}%</span>
                        </template>
                      </el-table-column>
                      <el-table-column label="命中指标" min-width="200">
                        <template #default="{ row }">
                          <span v-for="ind in row.hit_indicators" :key="ind" class="hit-tag">{{ ind }}</span>
                        </template>
                      </el-table-column>
                      <el-table-column prop="amount" label="成交额" width="70">
                        <template #default="{ row }">{{ row.amount }}亿</template>
                      </el-table-column>
                    </el-table>
                  </el-card>
                </el-col>
              </el-row>

              <!-- 市场情绪 -->
              <div class="emotion-bar" v-if="eastmoneyData.market_emotion">
                <span>市场情绪：</span>
                <span :class="eastmoneyData.market_emotion.up_ratio >= 50 ? 'text-red' : 'text-green'" style="font-weight: bold; font-size: 16px;">
                  {{ eastmoneyData.market_emotion.emotion_level }}
                </span>
                <span style="margin-left: 15px;">
                  上涨 <b class="text-red">{{ eastmoneyData.market_emotion.up_count }}</b> 家
                  下跌 <b class="text-green">{{ eastmoneyData.market_emotion.down_count }}</b> 家
                  ({{ eastmoneyData.market_emotion.up_ratio }}%)
                </span>
              </div>

              <el-row :gutter="20">
                <el-col :span="12">
                  <el-card>
                    <template #header>
                      <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span>🏆 龙头榜 (得分排名)</span>
                        <span v-if="eastmoneyData.leader_stocks?.top_leader" style="font-weight: normal; font-size: 12px;">
                          龙头: <b class="text-red">{{ eastmoneyData.leader_stocks.top_leader.name }}</b>
                          ({{ eastmoneyData.leader_stocks.top_leader.continuous }}板/{{ eastmoneyData.leader_stocks.top_leader.score }}分)
                        </span>
                      </div>
                    </template>
                    <el-table :data="eastmoneyData.leader_stocks?.leaders?.slice(0, 15) || []" height="350" stripe size="small">
                      <el-table-column prop="name" label="名称" width="70" />
                      <el-table-column prop="continuous" label="连板" width="50">
                        <template #default="{ row }">
                          <span class="text-red">{{ row.continuous }}</span>
                        </template>
                      </el-table-column>
                      <el-table-column prop="score" label="得分" width="50">
                        <template #default="{ row }">
                          <b :class="row.is_leader ? 'text-red' : ''">{{ row.score }}</b>
                        </template>
                      </el-table-column>
                      <el-table-column prop="first_time" label="首封" width="55" />
                      <el-table-column prop="amount" label="成交额" width="55">
                        <template #default="{ row }">{{ row.amount }}亿</template>
                      </el-table-column>
                      <el-table-column prop="turnover" label="换手" width="50">
                        <template #default="{ row }">{{ row.turnover }}%</template>
                      </el-table-column>
                    </el-table>
                  </el-card>
                </el-col>
                <el-col :span="12">
                  <el-card>
                    <template #header>💰 板块资金流向</template>
                    <el-table :data="eastmoneyData.sector_flow || []" height="350" stripe size="small">
                      <el-table-column prop="name" label="板块" width="90" />
                      <el-table-column prop="pct_chg" label="涨跌" width="60">
                        <template #default="{ row }">
                          <span :class="row.pct_chg >= 0 ? 'text-red' : 'text-green'">{{ row.pct_chg }}%</span>
                        </template>
                      </el-table-column>
                      <el-table-column prop="main_net" label="主力净(亿)" width="80">
                        <template #default="{ row }">
                          <span :class="row.main_net >= 0 ? 'text-red' : 'text-green'">{{ row.main_net }}</span>
                        </template>
                      </el-table-column>
                      <el-table-column prop="main_pct" label="占比%" width="60" />
                    </el-table>
                  </el-card>
                </el-col>
              </el-row>

              <el-row :gutter="20" style="margin-top: 15px">
                <el-col :span="12">
                  <el-card>
                    <template #header>
                      ⬆️ 弱转强 ({{ eastmoneyData.strength_change?.weak_to_strong_count || 0 }})
                    </template>
                    <el-table :data="eastmoneyData.strength_change?.weak_to_strong || []" height="280" stripe size="small">
                      <el-table-column prop="code" label="代码" width="70" />
                      <el-table-column prop="name" label="名称" width="70" />
                      <el-table-column prop="open_chg" label="开盘" width="55">
                        <template #default="{ row }">
                          <span class="text-green">{{ row.open_chg }}%</span>
                        </template>
                      </el-table-column>
                      <el-table-column prop="pct_chg" label="收盘" width="55">
                        <template #default="{ row }">
                          <span class="text-red">{{ row.pct_chg }}%</span>
                        </template>
                      </el-table-column>
                      <el-table-column prop="strength" label="转强" width="50">
                        <template #default="{ row }">
                          <b class="text-red">{{ row.strength }}</b>
                        </template>
                      </el-table-column>
                    </el-table>
                  </el-card>
                </el-col>
                <el-col :span="12">
                  <el-card>
                    <template #header>
                      ⬇️ 强转弱 ({{ eastmoneyData.strength_change?.strong_to_weak_count || 0 }})
                    </template>
                    <el-table :data="eastmoneyData.strength_change?.strong_to_weak || []" height="280" stripe size="small">
                      <el-table-column prop="code" label="代码" width="70" />
                      <el-table-column prop="name" label="名称" width="70" />
                      <el-table-column prop="high_chg" label="最高" width="55">
                        <template #default="{ row }">
                          <span class="text-red">{{ row.high_chg }}%</span>
                        </template>
                      </el-table-column>
                      <el-table-column prop="pct_chg" label="收盘" width="55">
                        <template #default="{ row }">
                          <span :class="row.pct_chg >= 0 ? 'text-red' : 'text-green'">{{ row.pct_chg }}%</span>
                        </template>
                      </el-table-column>
                      <el-table-column prop="weakness" label="回落" width="50">
                        <template #default="{ row }">
                          <b class="text-green">{{ row.weakness }}</b>
                        </template>
                      </el-table-column>
                    </el-table>
                  </el-card>
                </el-col>
              </el-row>

              <el-row :gutter="20" style="margin-top: 15px">
                <el-col :span="12">
                  <el-card>
                    <template #header>
                      📈 北向资金 ({{ eastmoneyData.north_flow?.total || 0 }}亿)
                    </template>
                    <div style="padding: 10px 0; font-size: 13px;">
                      沪股通: <b :class="(eastmoneyData.north_flow?.hk_to_sh || 0) >= 0 ? 'text-red' : 'text-green'">
                        {{ eastmoneyData.north_flow?.hk_to_sh || 0 }}亿
                      </b>
                      &nbsp;&nbsp;
                      深股通: <b :class="(eastmoneyData.north_flow?.hk_to_sz || 0) >= 0 ? 'text-red' : 'text-green'">
                        {{ eastmoneyData.north_flow?.hk_to_sz || 0 }}亿
                      </b>
                    </div>
                    <el-table :data="eastmoneyData.north_flow?.top_holdings || []" height="230" stripe size="small">
                      <el-table-column prop="code" label="代码" width="70" />
                      <el-table-column prop="name" label="名称" width="80" />
                      <el-table-column prop="hold_market_cap" label="持仓(亿)" width="80" />
                      <el-table-column prop="hold_ratio" label="占比%" width="60" />
                    </el-table>
                  </el-card>
                </el-col>
                <el-col :span="12">
                  <el-card>
                    <template #header>
                      <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span>🐉 龙虎榜</span>
                        <el-button size="small" type="primary" link @click="window.open(`https://data.eastmoney.com/stock/tradedetail.html`, '_blank')">
                          东财详情 →
                        </el-button>
                      </div>
                    </template>
                    <el-table :data="eastmoneyData.dragon_tiger || []" height="280" stripe size="small">
                      <el-table-column prop="code" label="代码" width="70" />
                      <el-table-column prop="name" label="名称" width="70" />
                      <el-table-column prop="pct_chg" label="涨跌" width="55">
                        <template #default="{ row }">
                          <span :class="row.pct_chg >= 0 ? 'text-red' : 'text-green'">{{ row.pct_chg }}%</span>
                        </template>
                      </el-table-column>
                      <el-table-column prop="net_amount" label="净买入" width="70">
                        <template #default="{ row }">
                          <span :class="row.net_amount >= 0 ? 'text-red' : 'text-green'">{{ row.net_amount }}万</span>
                        </template>
                      </el-table-column>
                      <el-table-column prop="reason" label="原因" />
                    </el-table>
                  </el-card>
                </el-col>
              </el-row>

              <el-row :gutter="20" style="margin-top: 15px">
                <el-col :span="12">
                  <el-card>
                    <template #header>
                      <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span>
                          💪 分时强度 (个股>板块>大盘)
                          <span style="font-weight: normal; font-size: 12px; color: #909399;">
                            大盘: {{ eastmoneyData.relative_strength?.market_chg || 0 }}%
                          </span>
                        </span>
                        <el-button size="small" @click="openFullscreen('strength', '分时强度详情', eastmoneyData.relative_strength?.stocks || [])">
                          全屏
                        </el-button>
                      </div>
                    </template>
                    <el-table :data="eastmoneyData.relative_strength?.stocks?.slice(0, 15) || []" height="300" stripe size="small">
                      <el-table-column prop="code" label="代码" width="70" />
                      <el-table-column prop="name" label="名称" width="70" />
                      <el-table-column prop="stock_chg" label="涨幅" width="55">
                        <template #default="{ row }">
                          <span class="text-red">{{ row.stock_chg }}%</span>
                        </template>
                      </el-table-column>
                      <el-table-column prop="amount" label="成交额" width="60">
                        <template #default="{ row }">{{ row.amount }}亿</template>
                      </el-table-column>
                      <el-table-column prop="strength" label="强度" width="50">
                        <template #default="{ row }">
                          <span class="text-red">{{ row.strength }}</span>
                        </template>
                      </el-table-column>
                    </el-table>
                  </el-card>
                </el-col>
                <el-col :span="12">
                  <el-card>
                    <template #header>
                      📊 昨日涨停今日表现 (赚钱效应: {{ eastmoneyData.emotion_cycle?.profit_effect || 0 }}%)
                    </template>
                    <el-table :data="eastmoneyData.emotion_cycle?.yesterday_limit_up_performance?.slice(0, 15) || []" height="300" stripe size="small">
                      <el-table-column prop="code" label="代码" width="70" />
                      <el-table-column prop="name" label="名称" width="80" />
                      <el-table-column prop="pct_chg" label="今日涨跌" width="80">
                        <template #default="{ row }">
                          <span :class="row.pct_chg >= 0 ? 'text-red' : 'text-green'">{{ row.pct_chg }}%</span>
                        </template>
                      </el-table-column>
                      <el-table-column prop="amount" label="成交额(亿)" width="80" />
                    </el-table>
                  </el-card>
                </el-col>
              </el-row>

              <el-row :gutter="20" style="margin-top: 15px">
                <el-col :span="24">
                  <el-card>
                    <template #header>🔥 人气榜 (人气指数 = 涨幅×2 + 换手率 + 成交额/10)</template>
                    <div style="display: flex; flex-wrap: wrap; gap: 8px; padding: 10px 0; max-height: 180px; overflow-y: auto;">
                      <span v-for="stock in eastmoneyData.hot_stocks || []" :key="stock.code" class="hot-stock-tag">
                        <b>{{ stock.rank }}</b>. {{ stock.name }}
                        <span :class="stock.pct_chg >= 0 ? 'text-red' : 'text-green'">{{ stock.pct_chg }}%</span>
                        <span style="color: #909399; font-size: 10px;">热度{{ stock.hot_index }}</span>
                      </span>
                    </div>
                  </el-card>
                </el-col>
              </el-row>
            </template>
          </div>

          <!-- 策略分析 -->
          <div v-if="activeTab === 'strategy'" class="analysis-content">
            <StrategyAnalysisView
              :eastmoney-data="eastmoneyData"
              :current-date="currentDate"
            />
          </div>

        </div>
        <!-- core-content end -->

        <!-- 复盘笔记 - 常驻底部 -->
        <el-card style="margin-top: 15px">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <div style="display: flex; align-items: center; gap: 15px;">
                <span>📝 复盘笔记</span>
                <div class="history-dates">
                  <span
                    v-for="h in reviewHistory"
                    :key="h.trade_date"
                    class="date-tag"
                    :class="{ active: currentDate === h.trade_date.replace(/-/g, '') }"
                    @click="loadHistoryReview(h)"
                  >
                    {{ h.trade_date.slice(5) }}
                  </span>
                </div>
              </div>
              <el-button type="primary" size="small" @click="saveReviewNote">保存</el-button>
            </div>
          </template>
          <el-input
            v-model="reviewContent"
            type="textarea"
            :rows="6"
            placeholder="记录今日复盘内容..."
          />
        </el-card>

        <!-- 全屏弹窗 -->
        <el-dialog v-model="showFullscreen" :title="fullscreenTitle" fullscreen>
          <el-table :data="fullscreenData" height="calc(100vh - 150px)" stripe>
            <el-table-column prop="code" label="代码" width="80" fixed />
            <el-table-column prop="name" label="名称" width="80" fixed />
            <el-table-column prop="sector" label="板块" width="100" />
            <el-table-column prop="price" label="现价" width="80" />
            <el-table-column prop="stock_chg" label="涨幅%" width="80">
              <template #default="{ row }">
                <span class="text-red">{{ row.stock_chg }}%</span>
              </template>
            </el-table-column>
            <el-table-column prop="sector_chg" label="板块%" width="80">
              <template #default="{ row }">
                <span :class="row.sector_chg >= 0 ? 'text-red' : 'text-green'">{{ row.sector_chg }}%</span>
              </template>
            </el-table-column>
            <el-table-column prop="strength" label="强度" width="70">
              <template #default="{ row }">
                <span class="text-red">{{ row.strength }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="amount" label="成交额(亿)" width="90" />
            <el-table-column prop="turnover" label="换手率%" width="80" />
            <el-table-column prop="volume_ratio" label="量比" width="70" />
            <el-table-column prop="speed" label="涨速%" width="70" />
            <el-table-column prop="open" label="开盘" width="80" />
            <el-table-column prop="high" label="最高" width="80" />
            <el-table-column prop="low" label="最低" width="80" />
            <el-table-column prop="pre_close" label="昨收" width="80" />
          </el-table>
        </el-dialog>

        <!-- 个股缠论分析Dialog -->
        <el-dialog
          v-model="showChanDetail"
          :title="`📈 ${chanDetailStock.name || chanDetailStock.ts_code} 缠论分析`"
          width="80%"
          @close="chanDetailData = {}; trendAnalysis = {}; multiPeriodData = {}"
        >
          <div v-loading="chanDetailLoading" style="min-height: 200px;">
            <el-row :gutter="20" v-if="!chanDetailLoading">
              <!-- 基本信息 -->
              <el-col :span="24">
                <el-card>
                  <template #header>📊 基本信息</template>
                  <el-row :gutter="20">
                    <el-col :span="6">
                      <span class="label">代码: {{ chanDetailStock.ts_code || chanDetailStock.code }}</span>
                    </el-col>
                    <el-col :span="6">
                      <span class="label">名称: {{ chanDetailStock.name }}</span>
                    </el-col>
                    <el-col :span="6">
                      <span class="label">行业: {{ chanDetailStock.industry }}</span>
                    </el-col>
                    <el-col :span="6">
                      <span class="label">价格: {{ chanDetailStock.price || chanDetailStock.close }}</span>
                    </el-col>
                  </el-row>
                </el-card>
              </el-col>

              <!-- 趋势分析 -->
              <el-col :span="12" v-if="trendAnalysis.type">
                <el-card>
                  <template #header>📈 趋势分析</template>
                  <div style="padding: 10px;">
                    <p><strong>趋势:</strong> <span :class="trendAnalysis.type === '上涨' ? 'text-red' : 'text-green'">{{ trendAnalysis.type }}</span></p>
                    <p><strong>阶段:</strong> {{ trendAnalysis.phase }}</p>
                    <p><strong>中枢:</strong> {{ trendAnalysis.hub_count }}</p>
                  </div>
                </el-card>
              </el-col>

              <!-- 背驰信息 -->
              <el-col :span="12" v-if="trendAnalysis.divergence">
                <el-card>
                  <template #header>🔄 背驰</template>
                  <div style="padding: 10px;">
                    <p><strong>类型:</strong> <span :class="trendAnalysis.divergence.is_diverge ? 'text-red' : ''">{{ trendAnalysis.divergence.is_diverge ? trendAnalysis.divergence.type : '无' }}</span></p>
                    <p><strong>强度:</strong> {{ ((trendAnalysis.divergence?.strength || 0) * 100).toFixed(0) }}%</p>
                  </div>
                </el-card>
              </el-col>

              <!-- 多周期分析 -->
              <el-col :span="24" v-if="multiPeriodData.signal">
                <el-card>
                  <template #header>🎯 多周期</template>
                  <el-row :gutter="20">
                    <el-col :span="8"><p><strong>日线:</strong> {{ multiPeriodData.daily?.type }}</p></el-col>
                    <el-col :span="8"><p><strong>30m:</strong> {{ multiPeriodData.min30?.type }}</p></el-col>
                    <el-col :span="8"><p><strong>5m:</strong> {{ multiPeriodData.min5?.type }}</p></el-col>
                  </el-row>
                  <p style="color: #e6a23c; font-weight: bold;">信号: {{ multiPeriodData.signal }} (信心 {{ ((multiPeriodData.confidence || 0) * 100).toFixed(0) }}%)</p>
                </el-card>
              </el-col>
            </el-row>
          </div>
        </el-dialog>

        <!-- 更多分析抽屉 -->
        <el-drawer
          v-model="showAnalysisDrawer"
          title="更多分析工具"
          direction="rtl"
          size="320px"
        >
          <div class="analysis-menu">
            <div
              v-for="item in analysisMenuItems"
              :key="item.name"
              class="analysis-menu-item"
              @click="openAnalysis(item.name)"
            >
              <span class="menu-icon">{{ item.icon }}</span>
              <div class="menu-info">
                <span class="menu-label">{{ item.label }}</span>
                <span class="menu-desc">{{ item.desc }}</span>
              </div>
              <el-icon class="menu-arrow"><ArrowRight /></el-icon>
            </div>
          </div>
        </el-drawer>

        <!-- 设置抽屉 -->
        <el-drawer
          v-model="showSettingsDrawer"
          title="设置"
          direction="rtl"
          size="320px"
        >
          <div class="settings-panel">
            <div class="setting-item">
              <span class="setting-label">数据源</span>
              <el-select v-model="dataSource" size="small" style="width: 140px">
                <el-option label="东财/同花顺" value="eastmoney" />
                <el-option label="Tushare" value="tushare" />
              </el-select>
            </div>
            <div class="setting-item">
              <span class="setting-label">涨跌颜色</span>
              <el-switch
                v-model="useBlueUp"
                active-text="蓝涨绿跌"
                inactive-text="红涨绿跌"
              />
            </div>
            <div class="setting-item">
              <span class="setting-label">自动刷新</span>
              <el-switch
                v-model="autoRefresh"
                @change="toggleAutoRefresh"
              />
            </div>
            <div class="setting-item" v-if="autoRefresh">
              <span class="setting-label">刷新状态</span>
              <span v-if="isTradeTime" class="status-text active">
                {{ refreshInterval }}s后刷新
              </span>
              <span v-else class="status-text">非交易时段</span>
            </div>
            <el-divider />
            <div class="setting-item">
              <el-button type="primary" @click="syncData" :loading="syncing" style="width: 100%">
                同步全部数据
              </el-button>
            </div>
          </div>
        </el-drawer>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Setting, ArrowRight } from '@element-plus/icons-vue'
import StrategyAnalysisView from './components/strategy/StrategyAnalysisView.vue'
import DashboardView from './components/dashboard/DashboardView.vue'
// 新核心组件
import TodayDecision from './components/decision/TodayDecision.vue'
import MyHoldings from './components/holdings/MyHoldings.vue'
import SmartPicks from './components/picks/SmartPicks.vue'
import AlertCenter from './components/alerts/AlertCenter.vue'
import {
  getTodayOrLastTradingDay,
  getLastTradingDay,
  getDatePickerDisabledDate,
  isTradingDay,
  getTradingStatusText,
  formatDateToDisplay,
} from './utils/tradingDayUtils'
import {
  getVolumeTop,
  getOversold,
  getKDJBottom,
  getMACDGolden,
  getBottomVolume,
  getIndustryHot,
  getMarketIndex,
  getCounterTrend,
  getMarketStats,
  getLimitUpList,
  getLimitDownList,
  getDragonTiger,
  getNorthBuy,
  getMarginBuy,
  getBreakout,
  getTopVolume,
  getGapUp,
  getGapDown,
  getIndustryGap,
  getReview,
  getReviewHistory,
  saveReview,
  syncDaily,
  calcIndicators,
  crawlEastmoney,
  crawlTushare,
  getEastmoneyData,
  getChanBottomDiverge,
  getChanTopDiverge,
  getChanFirstBuy,
  getChanSecondBuy,
  getChanThirdBuy,
  getChanHubShake,
  getChanData,
  calcChan,
  getTrendAnalysis,
  getMultiPeriodAnalysis,
  scanMarket,
  getKaipanlaFullEmotion,
  getFullAnalysis,
} from './api/stock'

// 初始化为最后一个交易日
const currentDate = ref(getTodayOrLastTradingDay())

// 日期选择器禁用函数
const disabledDate = getDatePickerDisabledDate()

// 交易日期状态提示
const tradingDateStatus = computed(() => {
  if (!currentDate.value) return ''
  const dateStr = currentDate.value
  const date = new Date(dateStr.substring(0, 4), parseInt(dateStr.substring(4, 6)) - 1, dateStr.substring(6, 8))
  return getTradingStatusText(date)
})
const syncing = ref(false)
const crawling = ref(false)
const activeTab = ref('decision')  // 默认显示今日决策
const autoRefresh = ref(false)
const refreshInterval = ref(30)
const dataSource = ref('eastmoney')

// Dashboard 相关数据
const analysisData = ref({})
const kaipanlaData = ref({})
const useBlueUp = ref(true) // 默认蓝涨
let refreshTimer = null
let countdownTimer = null

// 涨跌颜色class
const upClass = computed(() => useBlueUp.value ? 'text-blue' : 'text-red')
const downClass = computed(() => 'text-green')

// 抽屉状态
const showAnalysisDrawer = ref(false)
const showSettingsDrawer = ref(false)

// 核心导航项
const coreNavItems = [
  { name: 'decision', label: '今日决策', icon: '🎯' },
  { name: 'holdings', label: '我的持仓', icon: '💼' },
  { name: 'picks', label: '智能选股', icon: '🔍' },
  { name: 'alerts', label: '预警中心', icon: '🔔' }
]

// 分析菜单项
const analysisMenuItems = [
  { name: 'dashboard', label: '市场总览', icon: '🏠', desc: '大盘概况、情绪走势' },
  { name: 'volume', label: '量价分析', icon: '📈', desc: '成交额、量比、放量' },
  { name: 'indicator', label: '技术指标', icon: '📊', desc: 'RSI、MACD、KDJ' },
  { name: 'chan', label: '缠论选股', icon: '🔮', desc: '分型、笔、中枢、买卖点' },
  { name: 'money', label: '板块资金', icon: '💰', desc: '行业资金、北向、龙虎榜' },
  { name: 'limit', label: '涨跌停', icon: '🎯', desc: '涨停池、跌停池' },
  { name: 'pattern', label: '形态信号', icon: '⚡', desc: '突破、缺口、异动' },
  { name: 'eastmoney', label: '东财数据', icon: '🔥', desc: '爬虫数据详情' },
  { name: 'strategy', label: '策略分析', icon: '🎯', desc: '多维度策略回测' }
]

// 打开分析功能
const openAnalysis = (name) => {
  activeTab.value = name
  showAnalysisDrawer.value = false
}

// 情绪阶段样式
const getEmotionClass = computed(() => {
  const phase = eastmoneyData.value?.market_emotion?.emotion_phase
  if (phase === 'high_tide') return 'emotion-hot'
  if (phase === 'ice_point') return 'emotion-cold'
  if (phase === 'ebb_tide') return 'emotion-warning'
  return 'emotion-normal'
})

// 数据
const volumeTop = ref([])
const oversold = ref([])
const kdjBottom = ref([])
const macdGolden = ref([])
const bottomVolume = ref([])
const industryHot = ref([])
const marketIndex = ref([])
const counterTrend = ref([])
const marketStats = ref({ limitUp: 0, limitDown: 0, northFlow: 0 })
const limitUpList = ref([])
const limitDownList = ref([])
const dragonTiger = ref([])
const northBuy = ref([])
const marginBuy = ref([])
const breakout = ref([])
const topVolume = ref([])
const gapUp = ref([])
const gapDown = ref([])
const industryGap = ref([])
const eastmoneyData = ref(null)
const reviewContent = ref('')
const reviewHistory = ref([])
const showFullscreen = ref(false)
const fullscreenType = ref('')
const fullscreenTitle = ref('')
const fullscreenData = ref([])

// 缠论数据
const chanBottomDiverge = ref([])
const chanTopDiverge = ref([])
const chanFirstBuy = ref([])
const chanSecondBuy = ref([])
const chanThirdBuy = ref([])
const chanHubShake = ref([])
const chanCalcing = ref(false)

// 个股缠论分析
const showChanDetail = ref(false)
const chanDetailStock = ref({})
const chanDetailData = ref({})
const trendAnalysis = ref({})
const multiPeriodData = ref({})
const chanDetailLoading = ref(false)

// 判断是否非交易日 (周末或数据为空)
const isNonTradingDay = computed(() => {
  if (!eastmoneyData.value) return false
  // 检查涨停数据是否为空
  const limitUpCount = eastmoneyData.value.limit_up_down?.limit_up_count || 0
  const yesterdayCount = eastmoneyData.value.emotion_cycle?.yesterday_limit_up_performance?.length || 0
  // 如果涨停和昨日涨停都为0，很可能是非交易日
  return limitUpCount === 0 && yesterdayCount === 0
})

// 判断是否在交易时间 (周一到周五 9:15-15:00)
const isTradeTime = computed(() => {
  const now = new Date()
  const day = now.getDay()
  const hour = now.getHours()
  const minute = now.getMinutes()
  const time = hour * 60 + minute

  // 周末不交易
  if (day === 0 || day === 6) return false

  // 交易时间: 9:15-11:30, 13:00-15:00
  const morning1 = 9 * 60 + 15   // 9:15
  const morning2 = 11 * 60 + 30  // 11:30
  const afternoon1 = 13 * 60     // 13:00
  const afternoon2 = 15 * 60     // 15:00

  return (time >= morning1 && time <= morning2) || (time >= afternoon1 && time <= afternoon2)
})

// 切换自动刷新
const toggleAutoRefresh = (val) => {
  if (val) {
    startAutoRefresh()
  } else {
    stopAutoRefresh()
  }
}

// 开始自动刷新
const startAutoRefresh = () => {
  stopAutoRefresh()

  if (!isTradeTime.value) {
    ElMessage.warning('当前非交易时段，自动刷新已开启但暂不执行')
  }

  // 每30秒刷新一次
  refreshInterval.value = 30

  // 倒计时
  countdownTimer = setInterval(() => {
    if (isTradeTime.value) {
      refreshInterval.value--
      if (refreshInterval.value <= 0) {
        refreshInterval.value = 30
      }
    }
  }, 1000)

  // 定时刷新
  refreshTimer = setInterval(async () => {
    if (isTradeTime.value && !crawling.value) {
      await crawlData()
    }
  }, 30000)
}

// 停止自动刷新
const stopAutoRefresh = () => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
  if (countdownTimer) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
  refreshInterval.value = 30
}

// 获取指数名称
const getIndexName = (code) => {
  const names = { '000001.SH': '上证', '399001.SZ': '深证', '399006.SZ': '创业板' }
  return names[code] || code
}

// 格式化数字
const formatNumber = (num) => num ? (num / 10000).toFixed(0) + '万' : '-'
const formatAmount = (num) => num ? (num / 10000).toFixed(0) + '万' : '-'

// 导航到指定标签页
const navigateToTab = (tabName) => {
  activeTab.value = tabName
}

// 添加到持仓
const addToHoldings = (stock) => {
  // 切换到持仓页面，数据由持仓组件处理
  activeTab.value = 'holdings'
  ElMessage.success(`已将 ${stock.name} 添加到持仓，请在持仓页面完善信息`)
}

// 加载数据
const loadData = async () => {
  try {
    const date = currentDate.value
    const results = await Promise.all([
      getVolumeTop(date),
      getOversold(date),
      getKDJBottom(date),
      getMACDGolden(date),
      getBottomVolume(date),
      getIndustryHot(date),
      getMarketIndex(date),
      getCounterTrend(date),
      getMarketStats(date),
      getLimitUpList(date),
      getLimitDownList(date),
      getDragonTiger(date),
      getNorthBuy(date),
      getMarginBuy(date),
      getBreakout(date),
      getTopVolume(date),
      getGapUp(date),
      getGapDown(date),
      getIndustryGap(date),
      getReview(date.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')),
      getReviewHistory(),
    ])

    volumeTop.value = results[0] || []
    oversold.value = results[1] || []
    kdjBottom.value = results[2] || []
    macdGolden.value = results[3] || []
    bottomVolume.value = results[4] || []
    industryHot.value = results[5] || []
    marketIndex.value = results[6] || []
    counterTrend.value = results[7] || []
    marketStats.value = results[8] || { limitUp: 0, limitDown: 0, northFlow: 0 }
    limitUpList.value = results[9] || []
    limitDownList.value = results[10] || []
    dragonTiger.value = results[11] || []
    northBuy.value = results[12] || []
    marginBuy.value = results[13] || []
    breakout.value = results[14] || []
    topVolume.value = results[15] || []
    gapUp.value = results[16] || []
    gapDown.value = results[17] || []
    industryGap.value = results[18] || []
    reviewContent.value = results[19]?.content || ''
    reviewHistory.value = results[20] || []
  } catch (err) {
    ElMessage.error('加载数据失败: ' + err.message)
  }
}

// 同步数据
const syncData = async () => {
  syncing.value = true
  try {
    await syncDaily(currentDate.value)
    await calcIndicators(currentDate.value)
    await loadData()
    ElMessage.success('数据同步完成')
  } catch (err) {
    ElMessage.error('同步失败: ' + err.message)
  } finally {
    syncing.value = false
  }
}

// 爬取数据 (根据数据源)
const crawlData = async () => {
  crawling.value = true
  try {
    let data
    if (dataSource.value === 'tushare') {
      data = await crawlTushare(currentDate.value)
      ElMessage.success('Tushare数据爬取完成')
    } else {
      data = await crawlEastmoney(currentDate.value)
      ElMessage.success('东财/同花顺数据爬取完成')
    }
    eastmoneyData.value = data

    // 同时加载开盘啦数据
    try {
      const kplData = await getKaipanlaFullEmotion(currentDate.value)
      kaipanlaData.value = kplData || {}
    } catch (kplErr) {
      console.warn('开盘啦数据加载失败:', kplErr)
    }

    // 加载策略分析数据
    try {
      const emotionInput = buildEmotionInput()
      const marketInput = buildMarketInput()
      const analysis = await getFullAnalysis(emotionInput, marketInput, [])
      analysisData.value = analysis || {}
    } catch (analysisErr) {
      console.warn('策略分析失败:', analysisErr)
    }
  } catch (err) {
    ElMessage.error('爬取失败: ' + err.message)
  } finally {
    crawling.value = false
  }
}

// 构建情绪输入数据
const buildEmotionInput = () => {
  const data = eastmoneyData.value || {}
  const kpl = kaipanlaData.value || {}

  return {
    limit_up_count: kpl.limit_up?.count || data.limit_up_down?.limit_up_count || 0,
    max_continuous: kpl.continuous_ladder?.max_height || 0,
    up_ratio: (data.market_emotion?.up_ratio || 50) / 100,
    broken_count: kpl.broken_board?.count || 0,
    total_limit_up_attempt: (kpl.limit_up?.count || 0) + (kpl.broken_board?.count || 0),
    yesterday_score: 50
  }
}

// 构建市场输入数据
const buildMarketInput = () => {
  const data = eastmoneyData.value || {}
  const sectors = data.sector_flow || []

  return {
    box_pos: 50,
    pct_chg: data.sector_strength?.market_chg || 0,
    north_flow: data.north_flow?.total || 0,
    north_flow_avg_5d: 0,
    up_sectors: sectors.filter(s => s.pct_chg > 0).length,
    down_sectors: sectors.filter(s => s.pct_chg < 0).length,
    vol_ratio: 1.0,
    sector_avg_pct_chg: sectors.reduce((sum, s) => sum + (s.pct_chg || 0), 0) / sectors.length || 0,
    sectors: sectors.slice(0, 10).map(s => ({
      name: s.name,
      pct_chg: s.pct_chg,
      main_net: s.main_net
    }))
  }
}

// 保存复盘笔记
const saveReviewNote = async () => {
  try {
    const date = currentDate.value.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')
    await saveReview(date, reviewContent.value)
    ElMessage.success('保存成功')
    const history = await getReviewHistory()
    reviewHistory.value = history || []
  } catch (err) {
    ElMessage.error('保存失败: ' + err.message)
  }
}

// 加载历史复盘记录
const loadHistoryReview = async (row) => {
  const dateStr = row.trade_date.replace(/-/g, '')
  currentDate.value = dateStr
  await loadData()
}

// 加载缠论数据
const loadChanData = async () => {
  try {
    const date = currentDate.value
    const results = await Promise.all([
      getChanBottomDiverge(date),
      getChanTopDiverge(date),
      getChanFirstBuy(date),
      getChanSecondBuy(date),
      getChanThirdBuy(date),
      getChanHubShake(date),
    ])
    chanBottomDiverge.value = results[0] || []
    chanTopDiverge.value = results[1] || []
    chanFirstBuy.value = results[2] || []
    chanSecondBuy.value = results[3] || []
    chanThirdBuy.value = results[4] || []
    chanHubShake.value = results[5] || []
  } catch (err) {
    console.error('加载缠论数据失败:', err)
  }
}

// 计算缠论指标
const calcChanIndicators = async () => {
  chanCalcing.value = true
  try {
    await calcChan(currentDate.value)
    await loadChanData()
    ElMessage.success('缠论指标计算完成')
  } catch (err) {
    ElMessage.error('计算失败: ' + err.message)
  } finally {
    chanCalcing.value = false
  }
}

// 打开全屏查看
const openFullscreen = (type, title, data) => {
  fullscreenType.value = type
  fullscreenTitle.value = title
  fullscreenData.value = data
  showFullscreen.value = true
}

// 打开个股缠论分析
const openChanDetail = async (stock) => {
  showChanDetail.value = true
  chanDetailStock.value = stock
  chanDetailLoading.value = true
  try {
    const tsCode = stock.ts_code || stock.code
    // 并行加载各种分析数据
    const [trend, multiPeriod, chan] = await Promise.allSettled([
      getTrendAnalysis(tsCode).catch(() => ({})),
      getMultiPeriodAnalysis(tsCode).catch(() => ({})),
      getChanData(tsCode).catch(() => ({}))
    ])

    trendAnalysis.value = trend.value || {}
    multiPeriodData.value = multiPeriod.value || {}
    chanDetailData.value = chan.value || {}
  } catch (err) {
    console.error('加载个股分析失败:', err)
  } finally {
    chanDetailLoading.value = false
  }
}

// 获取周期阶段样式
const getCycleClass = (phase) => {
  const classes = {
    '高潮期': 'phase-climax',
    '回暖期': 'phase-warm',
    '修复期': 'phase-repair',
    '退潮期': 'phase-ebb',
    '冰点期': 'phase-freeze',
  }
  return classes[phase] || ''
}

// 自动加载东财数据
const autoLoadEastmoneyData = async () => {
  const now = new Date()
  const hour = now.getHours()
  const day = now.getDay()

  // 工作日15点后自动加载
  if (day >= 1 && day <= 5 && hour >= 15) {
    try {
      // 先尝试获取缓存数据
      const cached = await getEastmoneyData(currentDate.value)
      if (cached) {
        eastmoneyData.value = cached
        ElMessage.success('已加载今日缓存数据')
      } else {
        // 没有缓存，自动爬取
        ElMessage.info('正在自动获取今日数据...')
        crawling.value = true
        const data = await crawlEastmoney(currentDate.value)
        eastmoneyData.value = data
        ElMessage.success('今日数据获取完成')
        crawling.value = false
      }
    } catch (err) {
      console.error('自动加载失败:', err)
    }
  }
}

onMounted(() => {
  loadData()
  autoLoadEastmoneyData()
})

onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<style>
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: linear-gradient(135deg, #0f1419 0%, #1a252f 100%);
  min-height: 100vh;
}

.app-container {
  min-height: 100vh;
  color: #fff;
}

/* 新版头部样式 */
.app-header {
  background: linear-gradient(135deg, #1a252f 0%, #243447 100%);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  height: 60px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 24px;
}

.app-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #fff;
}

.market-quick-info {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.info-label {
  color: rgba(255, 255, 255, 0.5);
}

.info-value {
  font-weight: 600;
}

.info-value.up {
  color: #ff4d4f;
}

.info-value.down {
  color: #00b96b;
}

.info-value.emotion-hot {
  color: #ff4d4f;
}

.info-value.emotion-cold {
  color: #1890ff;
}

.info-value.emotion-warning {
  color: #faad14;
}

.info-value.emotion-normal {
  color: #00b96b;
}

.info-divider {
  color: rgba(255, 255, 255, 0.2);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 主内容区 */
.app-main {
  padding: 20px 24px;
  background: transparent;
}

/* 核心导航 */
.core-nav {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: linear-gradient(135deg, #1a252f 0%, #243447 100%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  color: rgba(255, 255, 255, 0.7);
}

.nav-item:hover {
  border-color: rgba(255, 255, 255, 0.2);
  transform: translateY(-2px);
}

.nav-item.active {
  background: linear-gradient(135deg, #00b96b 0%, #52c41a 100%);
  border-color: transparent;
  color: #fff;
  box-shadow: 0 4px 12px rgba(0, 185, 107, 0.3);
}

.nav-icon {
  font-size: 18px;
}

.nav-label {
  font-size: 14px;
  font-weight: 500;
}

.nav-item.more-btn {
  margin-left: auto;
  background: rgba(255, 255, 255, 0.05);
}

.nav-item.more-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.arrow-icon {
  font-size: 12px;
  margin-left: 4px;
}

/* 核心内容区 */
.core-content {
  background: linear-gradient(135deg, #1a252f 0%, #243447 100%);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  min-height: calc(100vh - 180px);
  overflow: hidden;
}

/* 分析菜单样式 */
.analysis-menu {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.analysis-menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.analysis-menu-item:hover {
  background: rgba(0, 185, 107, 0.1);
}

.menu-icon {
  font-size: 24px;
}

.menu-info {
  flex: 1;
}

.menu-label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  margin-bottom: 2px;
}

.menu-desc {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
}

.menu-arrow {
  color: rgba(255, 255, 255, 0.3);
}

/* 设置面板样式 */
.settings-panel {
  padding: 8px 0;
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
}

.setting-label {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.8);
}

.status-text {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
}

.status-text.active {
  color: #00b96b;
}

/* 保留旧样式兼容 */
.el-header {
  background: transparent;
}

.el-header h1 {
  margin: 0;
  font-size: 20px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.market-index-bar {
  display: none;
}

.index-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 分析内容区样式 */
.analysis-content {
  padding: 20px;
}

.index-name {
  font-weight: 500;
  color: #606266;
}

.index-price {
  font-weight: 600;
}

.el-main {
  padding: 20px;
}

.el-tabs--card > .el-tabs__header {
  margin-bottom: 15px;
}

/* 修复 Tab 切换时内容显示问题 - Element Plus 兼容 */
.main-tabs :deep(.el-tabs__content) {
  overflow: visible;
}

.text-red {
  color: #f56c6c;
}

.text-blue {
  color: #409eff;
}

.text-green {
  color: #67c23a;
}

/* 蓝涨主题 */
.blue-theme .text-red {
  color: #409eff;
}

.blue-theme .stock-tag .text-red {
  color: #ffd700;
}

.el-card {
  margin-bottom: 0;
}

.el-card__header {
  padding: 12px 15px;
  font-weight: 600;
  font-size: 14px;
}

.history-dates {
  display: flex;
  gap: 8px;
}

.date-tag {
  padding: 4px 8px;
  background: #f0f2f5;
  border-radius: 4px;
  font-size: 12px;
  font-weight: normal;
  cursor: pointer;
  transition: all 0.2s;
}

.date-tag:hover {
  background: #e6f7ff;
  color: #409eff;
}

.date-tag.active {
  background: #409eff;
  color: #fff;
}

.emotion-bar {
  padding: 12px 20px;
  background: #fff;
  border-radius: 8px;
  margin-bottom: 15px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  font-size: 14px;
}

.hot-stock-tag {
  padding: 6px 12px;
  background: #f5f7fa;
  border-radius: 4px;
  font-size: 13px;
}

.hot-stock-tag b {
  color: #409eff;
}

/* 非交易日提示 */
.non-trading-notice {
  padding: 12px 20px;
  background: #fdf6ec;
  border: 1px solid #f5dab1;
  border-radius: 8px;
  margin-bottom: 15px;
  color: #e6a23c;
  font-size: 14px;
}

/* 情绪周期仪表盘 */
.cycle-dashboard {
  display: flex;
  gap: 20px;
  padding: 15px 20px;
  background: #fff;
  border-radius: 8px;
  margin-bottom: 15px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.cycle-main {
  flex: 0 0 200px;
  text-align: center;
  padding: 10px;
  border-right: 1px solid #eee;
}

.cycle-phase {
  font-size: 24px;
  font-weight: bold;
  padding: 8px 16px;
  border-radius: 8px;
  margin-bottom: 8px;
}

.phase-climax { background: #fef0f0; color: #f56c6c; }
.phase-warm { background: #fdf6ec; color: #e6a23c; }
.phase-repair { background: #f0f9eb; color: #67c23a; }
.phase-ebb { background: #f4f4f5; color: #909399; }
.phase-freeze { background: #ecf5ff; color: #409eff; }

.cycle-score {
  font-size: 14px;
  color: #606266;
  margin-bottom: 6px;
}

.cycle-score b {
  font-size: 18px;
  color: #303133;
}

.cycle-desc {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.cycle-strategy {
  font-size: 12px;
  color: #409eff;
  font-weight: 500;
}

.cycle-indicators {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  align-content: center;
}

.indicator-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px;
  background: #f5f7fa;
  border-radius: 6px;
}

.ind-name {
  font-size: 11px;
  color: #909399;
  margin-bottom: 4px;
}

.ind-value {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 2px;
}

.ind-score {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 3px;
}

.score-好 { background: #f0f9eb; color: #67c23a; }
.score-中 { background: #fdf6ec; color: #e6a23c; }
.score-差 { background: #fef0f0; color: #f56c6c; }

.cycle-chart {
  flex: 0 0 180px;
  padding: 10px;
  border-left: 1px solid #eee;
}

.chart-title {
  font-size: 12px;
  color: #909399;
  text-align: center;
  margin-bottom: 8px;
}

.bar-chart {
  display: flex;
  justify-content: space-around;
  align-items: flex-end;
  height: 80px;
}

.bar-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.bar {
  width: 20px;
  background: linear-gradient(to top, #409eff, #79bbff);
  border-radius: 3px 3px 0 0;
  min-height: 4px;
}

.bar-label {
  font-size: 10px;
  color: #909399;
  margin-top: 4px;
}

.bar-value {
  font-size: 10px;
  color: #303133;
  font-weight: 500;
}

/* 策略看板 */
.strategy-board {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
  padding: 15px 20px;
  margin-bottom: 15px;
  color: #fff;
}

.strategy-header {
  margin-bottom: 12px;
}

.strategy-title {
  font-size: 16px;
  font-weight: bold;
  margin-bottom: 4px;
}

.strategy-desc {
  font-size: 12px;
  opacity: 0.9;
}

.strategy-content {
  display: flex;
  gap: 20px;
}

.strategy-tips {
  flex: 1;
}

.tip-section {
  margin-bottom: 8px;
}

.tip-label {
  font-size: 12px;
  margin-right: 8px;
}

.tip-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 11px;
  margin-right: 6px;
  margin-bottom: 4px;
}

.tip-tag.focus {
  background: rgba(255, 255, 255, 0.3);
}

.tip-tag.avoid {
  background: rgba(0, 0, 0, 0.2);
}

.strategy-stocks {
  flex: 1;
}

.stock-label {
  font-size: 12px;
  margin-bottom: 6px;
}

.stock-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.stock-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
  font-size: 11px;
}

.stock-tag .text-red {
  color: #ffd700;
}

.tag-reason {
  font-size: 9px;
  opacity: 0.8;
}

/* 多指标命中 */
.indicator-stats {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.stat-tag {
  font-size: 10px;
  padding: 2px 6px;
  background: #f0f2f5;
  border-radius: 3px;
  color: #606266;
  font-weight: normal;
}

.hit-tag {
  display: inline-block;
  padding: 2px 6px;
  background: #ecf5ff;
  color: #409eff;
  border-radius: 3px;
  font-size: 10px;
  margin-right: 4px;
  margin-bottom: 2px;
}

/* 共振板块 */
.resonance-sector {
  padding: 8px 10px;
  border-bottom: 1px solid #f0f2f5;
}

.resonance-sector:last-child {
  border-bottom: none;
}

.sector-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.sector-name {
  font-weight: 600;
  font-size: 13px;
}

.sector-chg {
  font-size: 13px;
}

.sector-strength {
  font-size: 11px;
  color: #909399;
}

.sector-leaders {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.leader-tag {
  display: inline-block;
  padding: 2px 8px;
  background: #f5f7fa;
  border-radius: 3px;
  font-size: 11px;
}
</style>
