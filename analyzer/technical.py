"""
Technical Analyzer - 技术分析模块
提供全面的技术指标计算和分析
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class Trend(Enum):
    BULLISH = "bullish"      # 看涨
    BEARISH = "bearish"      # 看跌
    NEUTRAL = "neutral"      # 中性


class Signal(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class TechnicalIndicators:
    """技术指标集合"""
    # 移动平均线
    sma_5: Optional[float] = None
    sma_10: Optional[float] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    
    # MACD
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    
    # RSI
    rsi_14: Optional[float] = None
    
    # 布林带
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    bb_width: Optional[float] = None
    bb_position: Optional[float] = None  # %B指标
    
    # 成交量
    volume_sma: Optional[float] = None
    
    # KDJ (随机指标)
    k: Optional[float] = None
    d: Optional[float] = None
    j: Optional[float] = None
    
    # ATR (平均真实波幅)
    atr_14: Optional[float] = None
    
    # 信号
    trend: Trend = Trend.NEUTRAL
    signal: Signal = Signal.HOLD
    confidence: float = 0.0


class TechnicalAnalyzer:
    """技术分析器"""
    
    def __init__(self, df: pd.DataFrame):
        """
        初始化分析器
        
        Args:
            df: DataFrame with columns: open, high, low, close, volume
        """
        self.df = df.copy()
        self._ensure_columns()
    
    def _ensure_columns(self):
        """确保必要的列存在"""
        required = ['open', 'high', 'low', 'close', 'volume']
        for col in required:
            if col not in self.df.columns:
                # 尝试中文字段名
                cn_map = {'开盘': 'open', '最高': 'high', '最低': 'low', '收盘': 'close', '成交量': 'volume'}
                for cn, en in cn_map.items():
                    if cn in self.df.columns:
                        self.df[en] = self.df[cn]
                        break
    
    # ============== 移动平均线 ==============
    
    def calculate_sma(self, period: int) -> pd.Series:
        """计算简单移动平均线"""
        return self.df['close'].rolling(window=period).mean()
    
    def calculate_ema(self, period: int) -> pd.Series:
        """计算指数移动平均线"""
        return self.df['close'].ewm(span=period, adjust=False).mean()
    
    # ============== MACD ==============
    
    def calculate_macd(self, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """计算MACD指标"""
        ema_fast = self.calculate_ema(fast)
        ema_slow = self.calculate_ema(slow)
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal, adjust=False).mean()
        macd_hist = macd - macd_signal
        return macd, macd_signal, macd_hist
    
    # ============== RSI ==============
    
    def calculate_rsi(self, period: int = 14) -> pd.Series:
        """计算RSI指标"""
        delta = self.df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    # ============== 布林带 ==============
    
    def calculate_bollinger_bands(self, period: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """计算布林带"""
        middle = self.calculate_sma(period)
        std = self.df['close'].rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper, middle, lower
    
    # ============== KDJ ==============
    
    def calculate_kdj(self, n: int = 9, m1: int = 3, m2: int = 3) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """计算KDJ指标"""
        low_list = self.df['low'].rolling(window=n, min_periods=n).min()
        high_list = self.df['high'].rolling(window=n, min_periods=n).max()
        rsv = (self.df['close'] - low_list) / (high_list - low_list) * 100
        
        k = rsv.ewm(com=m1 - 1, adjust=False).mean()
        d = k.ewm(com=m2 - 1, adjust=False).mean()
        j = 3 * k - 2 * d
        
        return k, d, j
    
    # ============== ATR ==============
    
    def calculate_atr(self, period: int = 14) -> pd.Series:
        """计算ATR指标"""
        high_low = self.df['high'] - self.df['low']
        high_close = np.abs(self.df['high'] - self.df['close'].shift())
        low_close = np.abs(self.df['low'] - self.df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr = true_range.rolling(window=period).mean()
        return atr
    
    # ============== 综合分析 ==============
    
    def analyze(self) -> TechnicalIndicators:
        """执行完整技术分析"""
        if len(self.df) < 50:
            return TechnicalIndicators()
        
        indicators = TechnicalIndicators()
        
        # 移动平均线
        indicators.sma_5 = self.calculate_sma(5).iloc[-1]
        indicators.sma_10 = self.calculate_sma(10).iloc[-1]
        indicators.sma_20 = self.calculate_sma(20).iloc[-1]
        indicators.sma_50 = self.calculate_sma(50).iloc[-1] if len(self.df) >= 50 else None
        indicators.ema_12 = self.calculate_ema(12).iloc[-1]
        indicators.ema_26 = self.calculate_ema(26).iloc[-1]
        
        # MACD
        macd, macd_signal, macd_hist = self.calculate_macd()
        indicators.macd = macd.iloc[-1]
        indicators.macd_signal = macd_signal.iloc[-1]
        indicators.macd_histogram = macd_hist.iloc[-1]
        
        # RSI
        indicators.rsi_14 = self.calculate_rsi(14).iloc[-1]
        
        # 布林带
        bb_upper, bb_middle, bb_lower = self.calculate_bollinger_bands()
        indicators.bb_upper = bb_upper.iloc[-1]
        indicators.bb_middle = bb_middle.iloc[-1]
        indicators.bb_lower = bb_lower.iloc[-1]
        indicators.bb_width = (bb_upper.iloc[-1] - bb_lower.iloc[-1]) / bb_middle.iloc[-1]
        
        close = self.df['close'].iloc[-1]
        indicators.bb_position = (close - bb_lower.iloc[-1]) / (bb_upper.iloc[-1] - bb_lower.iloc[-1])
        
        # 成交量
        indicators.volume_sma = self.df['volume'].rolling(window=20).mean().iloc[-1]
        
        # KDJ
        k, d, j = self.calculate_kdj()
        indicators.k = k.iloc[-1]
        indicators.d = d.iloc[-1]
        indicators.j = j.iloc[-1]
        
        # ATR
        indicators.atr_14 = self.calculate_atr(14).iloc[-1]
        
        # 趋势判断
        indicators.trend = self._determine_trend(indicators)
        indicators.signal = self._generate_signal(indicators)
        indicators.confidence = self._calculate_confidence(indicators)
        
        return indicators
    
    def _determine_trend(self, ind: TechnicalIndicators) -> Trend:
        """判断趋势"""
        score = 0
        
        # 价格与移动平均线关系
        if ind.sma_5 and ind.sma_20:
            if ind.sma_5 > ind.sma_20:
                score += 1
            else:
                score -= 1
        
        # MACD
        if ind.macd and ind.macd_signal:
            if ind.macd > ind.macd_signal:
                score += 1
            else:
                score -= 1
        
        # RSI
        if ind.rsi_14:
            if ind.rsi_14 > 60:
                score += 0.5
            elif ind.rsi_14 < 40:
                score -= 0.5
        
        if score > 1:
            return Trend.BULLISH
        elif score < -1:
            return Trend.BEARISH
        return Trend.NEUTRAL
    
    def _generate_signal(self, ind: TechnicalIndicators) -> Signal:
        """生成交易信号"""
        score = 0
        
        # MACD金叉/死叉
        if ind.macd_histogram:
            if ind.macd_histogram > 0:
                score += 1
            else:
                score -= 1
        
        # RSI超卖/超买
        if ind.rsi_14:
            if ind.rsi_14 < 30:
                score += 2  # 强烈买入
            elif ind.rsi_14 > 70:
                score -= 2  # 强烈卖出
        
        # 布林带
        if ind.bb_position is not None:
            if ind.bb_position < 0.1:
                score += 1
            elif ind.bb_position > 0.9:
                score -= 1
        
        # KDJ
        if ind.j is not None:
            if ind.j < 20:
                score += 1
            elif ind.j > 80:
                score -= 1
        
        if score >= 2:
            return Signal.BUY
        elif score <= -2:
            return Signal.SELL
        return Signal.HOLD
    
    def _calculate_confidence(self, ind: TechnicalIndicators) -> float:
        """计算信号置信度"""
        # 基于多个指标的一致性计算置信度
        signals = []
        
        if ind.macd_histogram:
            signals.append(1 if ind.macd_histogram > 0 else -1)
        
        if ind.rsi_14:
            if ind.rsi_14 < 30:
                signals.append(1)
            elif ind.rsi_14 > 70:
                signals.append(-1)
        
        if ind.bb_position is not None:
            if ind.bb_position < 0.2:
                signals.append(1)
            elif ind.bb_position > 0.8:
                signals.append(-1)
        
        if not signals:
            return 0.0
        
        # 计算一致性
        avg_signal = sum(signals) / len(signals)
        confidence = abs(avg_signal) * 100
        return min(confidence, 100)
    
    def get_support_resistance(self, lookback: int = 20) -> Dict:
        """计算支撑阻力位"""
        recent = self.df.tail(lookback)
        
        # 简单方法：近期高低点
        resistance = recent['high'].max()
        support = recent['low'].min()
        
        # 枢轴点
        pivot = (recent['high'].iloc[-1] + recent['low'].iloc[-1] + recent['close'].iloc[-1]) / 3
        
        return {
            "support": support,
            "resistance": resistance,
            "pivot": pivot,
            "range": resistance - support
        }
    
    def detect_patterns(self) -> List[str]:
        """检测K线形态"""
        patterns = []
        
        if len(self.df) < 5:
            return patterns
        
        # 获取最近几根K线
        recent = self.df.tail(5)
        
        # 锤子线 (Hammer)
        for i in range(-3, 0):
            if i >= -len(recent):
                candle = recent.iloc[i]
                body = abs(candle['close'] - candle['open'])
                lower_shadow = min(candle['open'], candle['close']) - candle['low']
                upper_shadow = candle['high'] - max(candle['open'], candle['close'])
                
                if lower_shadow > 2 * body and upper_shadow < body:
                    patterns.append("锤子线 (潜在反转)")
                    break
        
        # 吞没形态 (Engulfing)
        if len(recent) >= 2:
            prev = recent.iloc[-2]
            curr = recent.iloc[-1]
            
            prev_body = abs(prev['close'] - prev['open'])
            curr_body = abs(curr['close'] - curr['open'])
            
            # 看涨吞没
            if (prev['close'] < prev['open'] and  # 前一根阴线
                curr['close'] > curr['open'] and   # 当前阳线
                curr['open'] < prev['close'] and   # 当前开盘低于前收
                curr['close'] > prev['open']):      # 当前收盘高于前开
                patterns.append("看涨吞没")
            
            # 看跌吞没
            if (prev['close'] > prev['open'] and
                curr['close'] < curr['open'] and
                curr['open'] > prev['close'] and
                curr['close'] < prev['open']):
                patterns.append("看跌吞没")
        
        return patterns
    
    def format_report(self, ind: TechnicalIndicators) -> str:
        """格式化分析报告"""
        lines = [
            "**技术分析报告**\n",
            f"趋势: {'🟢 看涨' if ind.trend == Trend.BULLISH else '🔴 看跌' if ind.trend == Trend.BEARISH else '⚪ 震荡'}",
            f"信号: {'💚 买入' if ind.signal == Signal.BUY else '❤️ 卖出' if ind.signal == Signal.SELL else '💛 持有'} (置信度: {ind.confidence:.1f}%)",
            "",
            "**技术指标**:",
        ]
        
        if ind.sma_20:
            lines.append(f"  SMA20: ${ind.sma_20:.2f}")
        if ind.ema_12 and ind.ema_26:
            lines.append(f"  EMA12/26: ${ind.ema_12:.2f} / ${ind.ema_26:.2f}")
        if ind.rsi_14:
            rsi_status = "超卖" if ind.rsi_14 < 30 else "超买" if ind.rsi_14 > 70 else "正常"
            lines.append(f"  RSI(14): {ind.rsi_14:.1f} ({rsi_status})")
        if ind.macd:
            lines.append(f"  MACD: {ind.macd:.3f}")
        if ind.bb_position is not None:
            bb_status = "下轨" if ind.bb_position < 0.2 else "上轨" if ind.bb_position > 0.8 else "中轨"
            lines.append(f"  布林带: %{ind.bb_position*100:.1f} ({bb_status})")
        
        # 支撑阻力
        sr = self.get_support_resistance()
        lines.extend([
            "",
            "**支撑阻力**:",
            f"  支撑: ${sr['support']:.2f}",
            f"  阻力: ${sr['resistance']:.2f}",
        ])
        
        # K线形态
        patterns = self.detect_patterns()
        if patterns:
            lines.extend(["", "**K线形态**:"])
            for p in patterns:
                lines.append(f"  • {p}")
        
        return "\n".join(lines)


if __name__ == "__main__":
    # 测试
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from data.market_data import MarketDataManager
    
    # 获取数据
    dm = MarketDataManager()
    df = dm.get_us_stock_data("NVDA", period="3mo")
    
    # 分析
    analyzer = TechnicalAnalyzer(df)
    indicators = analyzer.analyze()
    
    # 输出报告
    print(analyzer.format_report(indicators))
