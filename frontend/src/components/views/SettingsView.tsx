/**
 * 设置页面
 * 
 * 包含：
 * - 钉钉账号绑定
 * - 钉钉机器人配置
 * - 进度反馈历史
 * - 通知设置
 * - 其他系统设置
 */
import React from 'react';
import { Tabs, Card } from 'antd';
import {
  BellOutlined,
  LinkOutlined,
  SettingOutlined,
  ApiOutlined,
  HistoryOutlined
} from '@ant-design/icons';
import { 
  DingtalkBindingPanel,
  DingtalkConfigPanel,
  ProgressFeedbackHistory
} from '../dingtalk';

const { TabPane } = Tabs;

const SettingsView: React.FC = () => {
  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <Tabs defaultActiveKey="dingtalk">
          <TabPane
            tab={
              <span>
                <LinkOutlined />
                钉钉绑定
              </span>
            }
            key="dingtalk"
          >
            <DingtalkBindingPanel />
          </TabPane>
          
          <TabPane
            tab={
              <span>
                <ApiOutlined />
                钉钉配置
              </span>
            }
            key="dingtalk-config"
          >
            <DingtalkConfigPanel />
          </TabPane>
          
          <TabPane
            tab={
              <span>
                <HistoryOutlined />
                反馈历史
              </span>
            }
            key="feedback-history"
          >
            <ProgressFeedbackHistory />
          </TabPane>
          
          <TabPane
            tab={
              <span>
                <BellOutlined />
                通知设置
              </span>
            }
            key="notifications"
          >
            <div>通知设置功能开发中...</div>
          </TabPane>
          
          <TabPane
            tab={
              <span>
                <SettingOutlined />
                系统设置
              </span>
            }
            key="system"
          >
            <div>系统设置功能开发中...</div>
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default SettingsView;
