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
  algorithm: theme.defaultAlgorithm,
  token: {
    // 品牌色 — 亮色环境下的深黑强调
    colorPrimary: '#000000',
    colorPrimaryHover: '#333333',
    colorPrimaryActive: '#555555',

    // 功能色（低饱和度）
    colorSuccess: '#2F5A28',
    colorWarning: '#A67B1E',
    colorError: '#9F2F2D',
    colorInfo: '#666666', // 改为中性灰

    // 中性色（Taste Skill Light Organic）
    colorText: '#111111',
    colorTextHeading: '#000000',
    colorTextSecondary: '#666666',
    colorTextTertiary: '#999999',
    colorTextQuaternary: '#CCCCCC',
    colorBgContainer: 'transparent',
    colorBgLayout: 'transparent',
    colorBgElevated: '#FFFFFF',
    colorBorder: 'rgba(0, 0, 0, 0.08)',
    colorBorderSecondary: 'rgba(0, 0, 0, 0.04)',

    // 字体
    fontFamily: "var(--font-sans)",
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
      colorPrimary: '#000000',
      colorPrimaryHover: '#333333',
      colorPrimaryActive: '#555555',
      primaryColor: '#FFFFFF',
      defaultBg: '#FFFFFF',
      defaultBorderColor: 'rgba(0, 0, 0, 0.1)',
      defaultHoverBg: '#F9F9F9',
      defaultHoverBorderColor: 'rgba(0, 0, 0, 0.2)',
      defaultHoverColor: '#000000',
      defaultColor: '#111111',
    },
    Input: {
      colorBgContainer: 'rgba(255, 255, 255, 0.8)',
      colorBorder: 'rgba(0, 0, 0, 0.1)',
      hoverBorderColor: 'rgba(0, 0, 0, 0.2)',
      activeBorderColor: 'rgba(0, 0, 0, 0.3)',
      activeShadow: '0 0 0 2px rgba(0, 0, 0, 0.05)',
    },
    Select: {
      colorBgContainer: 'rgba(255, 255, 255, 0.8)',
      colorBorder: 'rgba(0, 0, 0, 0.1)',
      hoverBorderColor: 'rgba(0, 0, 0, 0.2)',
      activeBorderColor: 'rgba(0, 0, 0, 0.3)',
      activeShadow: '0 0 0 2px rgba(0, 0, 0, 0.05)',
      optionSelectedBg: 'rgba(0, 0, 0, 0.06)',
      optionActiveBg: 'rgba(0, 0, 0, 0.04)',
      optionSelectedColor: '#000000',
    },
    Card: {
      paddingLG: 24,
      colorBgContainer: 'transparent',
    },
    Menu: {
      itemBorderRadius: 6,
      itemMarginInline: 8,
      itemPaddingInline: 12,
      itemBg: 'transparent',
      subMenuItemBg: 'transparent',
      itemHoverBg: 'rgba(0, 0, 0, 0.04)',
      itemSelectedBg: 'rgba(0, 0, 0, 0.08)',
      itemSelectedColor: '#000000',
    },
    Modal: {
      borderRadiusLG: 12,
      contentBg: '#FFFFFF',
      headerBg: '#FFFFFF',
    },
    Drawer: {
      colorBgElevated: '#FFFFFF',
    },
    Table: {
      headerBg: 'rgba(0, 0, 0, 0.03)',
      headerColor: 'rgba(0, 0, 0, 0.65)',
      colorBgContainer: 'transparent',
    },
    Typography: {
      titleMarginBottom: '0.8em',
      titleMarginTop: '1.2em',
      fontFamilyCode: 'var(--font-mono)',
    },
    Segmented: {
      itemSelectedBg: '#FFFFFF',
      trackBg: 'rgba(0, 0, 0, 0.04)',
    },
    Tabs: {
      inkBarColor: '#000000',
      itemActiveColor: '#000000',
      itemSelectedColor: '#000000',
      itemHoverColor: '#333333',
    },
    Alert: {
      colorInfoBg: '#F7F7F7',
      colorInfoBorder: '#EAEAEA',
      colorInfo: '#555555',
    },
    Switch: {
      colorPrimary: '#737373',
      colorPrimaryHover: '#555555',
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
