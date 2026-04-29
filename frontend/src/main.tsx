import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ConfigProvider, theme } from 'antd';
import { HelmetProvider } from 'react-helmet-async';
import zhCN from 'antd/locale/zh_CN';
import dayjs from 'dayjs';
import 'dayjs/locale/zh-cn';
import App from './App';
import './index.css';

dayjs.locale('zh-cn');

/**
 * Ant Design 5 主题定制
 * 基于 Premium Utilitarian Minimalism 设计规范
 * 暖灰色系 + 低饱和度点缀色 + 扁平化组件
 */
const antdTheme = {
  algorithm: theme.darkAlgorithm,
  token: {
    // 品牌色 — 暗色环境下的高亮白
    colorPrimary: '#FFFFFF',
    colorPrimaryHover: 'rgba(255,255,255,0.8)',
    colorPrimaryActive: 'rgba(255,255,255,0.6)',

    // 功能色（低饱和度）
    colorSuccess: '#346538',
    colorWarning: '#956400',
    colorError: '#9F2F2D',
    colorInfo: '#1F6C9F',

    // 中性色（适配暗黑与毛玻璃）
    colorText: '#FFFFFF',
    colorTextSecondary: 'rgba(255, 255, 255, 0.7)',
    colorTextTertiary: 'rgba(255, 255, 255, 0.4)',
    colorTextQuaternary: 'rgba(255, 255, 255, 0.2)',
    colorBgContainer: 'transparent',
    colorBgLayout: 'transparent',
    colorBgElevated: 'rgba(20, 20, 20, 0.6)',
    colorBorder: 'rgba(255, 255, 255, 0.1)',
    colorBorderSecondary: 'rgba(255, 255, 255, 0.05)',

    // 字体
    fontFamily: "'Outfit', 'SF Pro Display', 'Helvetica Neue', system-ui, sans-serif",
    fontSize: 14,
    fontSizeHeading1: 28,
    fontSizeHeading2: 22,
    fontSizeHeading3: 18,
    fontSizeHeading4: 15,
    fontSizeHeading5: 13,

    // 圆角
    borderRadius: 6,
    borderRadiusLG: 8,
    borderRadiusSM: 4,

    // 阴影
    boxShadow: '0 1px 3px rgba(0,0,0,0.03)',
    boxShadowSecondary: '0 4px 16px rgba(0,0,0,0.06)',

    // 间距
    padding: 16,
    paddingLG: 24,
    paddingSM: 12,
    paddingXS: 8,
    margin: 16,
    marginLG: 24,
    marginSM: 12,
    marginXS: 8,

    // 控件
    controlHeight: 36,
    controlHeightLG: 42,
    controlHeightSM: 28,

    // 线条
    lineWidth: 1,
    lineType: 'solid' as const,

    // 动画
    motionDurationFast: '0.15s',
    motionDurationMid: '0.2s',
    motionDurationSlow: '0.3s',
    motionEaseInOut: 'cubic-bezier(0.16, 1, 0.3, 1)',
  },
  components: {
    Button: {
      primaryShadow: 'none',
      defaultShadow: 'none',
      dangerShadow: 'none',
      defaultBg: 'rgba(255, 255, 255, 0.05)',
      defaultBorderColor: 'rgba(255, 255, 255, 0.1)',
    },
    Card: {
      paddingLG: 20,
      colorBgContainer: 'transparent',
    },
    Menu: {
      itemBorderRadius: 6,
      itemMarginInline: 8,
      itemPaddingInline: 12,
      itemBg: 'transparent',
      subMenuItemBg: 'transparent',
    },
    Modal: {
      borderRadiusLG: 12,
      contentBg: 'transparent',
      headerBg: 'transparent',
    },
    Drawer: {
      colorBgElevated: 'transparent',
    },
    Table: {
      headerBg: 'rgba(255, 255, 255, 0.05)',
      headerColor: 'rgba(255, 255, 255, 0.7)',
      colorBgContainer: 'transparent',
    },
    Segmented: {
      itemSelectedBg: 'rgba(255, 255, 255, 0.1)',
      trackBg: 'rgba(255, 255, 255, 0.05)',
    },
    Tabs: {
      inkBarColor: '#FFFFFF',
      itemActiveColor: '#FFFFFF',
      itemSelectedColor: '#FFFFFF',
      itemHoverColor: 'rgba(255, 255, 255, 0.8)',
    },
  },
};

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <HelmetProvider>
      <ConfigProvider locale={zhCN} theme={antdTheme}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </ConfigProvider>
    </HelmetProvider>
  </React.StrictMode>
);
