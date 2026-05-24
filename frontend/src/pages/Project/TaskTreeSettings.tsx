import { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Button,
  Divider,
  message,
  Tabs,
  Switch,
  Input,
  InputNumber,
  Alert,
  Space,
  Checkbox,
} from 'antd';
import {
  SaveOutlined,
  BellOutlined,
} from '@ant-design/icons';
import { Helmet } from 'react-helmet-async';
import { reminderSettingsAPI } from '../../api';

export default function TaskTreeSettings() {
  const [reminderForm] = Form.useForm();
  const [loadingReminder, setLoadingReminder] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [loadingStats, setLoadingStats] = useState(false);
  const [statsData, setStatsData] = useState<any>(null);
  const [analysisConfig, setAnalysisConfig] = useState({
    overdue: true, progress_stalled: true, dependency_unblocked: true, team_load: true, risk_prediction: true,
  });

  const watchedEnabled = Form.useWatch('enabled', reminderForm);
  const watchedStreamEnabled = Form.useWatch('dingtalk_stream_enabled', reminderForm);

  useEffect(() => {
    const loadReminderSettings = async () => {
      try {
        const res = await reminderSettingsAPI.getSettings();
        if (res.code === 200 && res.data) {
          const ac = res.data.analysis_config || {};
          setAnalysisConfig({
            overdue: ac.overdue ?? true,
            progress_stalled: ac.progress_stalled ?? true,
            dependency_unblocked: ac.dependency_unblocked ?? true,
            team_load: ac.team_load ?? true,
            risk_prediction: ac.risk_prediction ?? true,
          });
          reminderForm.setFieldsValue({
            enabled: res.data.enabled,
            daily_limit: res.data.daily_limit || 5,
            dingtalk_webhook: res.data.dingtalk_webhook,
            dingtalk_secret: res.data.dingtalk_secret,
            dingtalk_client_id: res.data.dingtalk_client_id,
            dingtalk_client_secret: res.data.dingtalk_client_secret,
            dingtalk_stream_enabled: res.data.dingtalk_stream_enabled || false,
          });
        }
      } catch (error) {
        console.error('加载提醒设置失败:', error);
      }
    };
    loadReminderSettings();
  }, [reminderForm]);

  const handleSaveReminder = async (values: any) => {
    setLoadingReminder(true);
    try {
      const res = await reminderSettingsAPI.updateSettings({
        enabled: values.enabled,
        daily_limit: values.daily_limit || 5,
        analysis_config: analysisConfig,
        dingtalk_webhook: values.dingtalk_webhook,
        dingtalk_secret: values.dingtalk_secret,
        dingtalk_client_id: values.dingtalk_client_id,
        dingtalk_client_secret: values.dingtalk_client_secret,
        dingtalk_stream_enabled: values.dingtalk_stream_enabled || false,
      });
      if (res.code === 200) { message.success('智能提醒设置已保存'); }
      else { message.error(res.message || '保存失败'); }
    } catch (error: any) { 
      message.error(error.detail || error.message || '保存失败');
      console.error('保存智能提醒设置失败:', error);
    }
    finally { setLoadingReminder(false); }
  };

  const handleTriggerReminder = async () => {
    setTriggering(true);
    try {
      const res = await reminderSettingsAPI.trigger();
      if (res.code === 200) { message.success('提醒已发送'); }
      else { message.error(res.message || '发送失败'); }
    } catch (error: any) { message.error(error.message || '发送失败'); }
    finally { setTriggering(false); }
  };

  const handleLoadStats = async (days: number = 7) => {
    setLoadingStats(true);
    try {
      const res = await reminderSettingsAPI.getStats(days);
      if (res.code === 200) { setStatsData(res.data); }
    } catch (error) { console.error('加载统计失败:', error); }
    finally { setLoadingStats(false); }
  };

  const tabItems = [
    {
      key: 'reminder',
      label: <span><BellOutlined /> 智能提醒</span>,
      children: (
        <Card bordered={false}>
          <Alert message="智能提醒说明" description="开启智能提醒后，系统会定期使用大模型分析您的任务，并通过钉钉发送个性化提醒通知。" type="info" showIcon style={{ marginBottom: 24 }} />
          <Form form={reminderForm} layout="vertical" onFinish={handleSaveReminder} style={{ maxWidth: 600 }}>
            <Divider orientation="left">专属钉钉机器人</Divider>
            <Alert 
              message="钉钉接入方式" 
              description={
                <div>
                  <p><strong>Webhook模式：</strong>适用于有公网IP的服务器，钉钉主动推送消息到你的服务器</p>
                  <p><strong>Stream模式：</strong>适用于本地开发环境（无需公网IP），通过WebSocket主动连接钉钉服务器</p>
                </div>
              } 
              type="info" 
              showIcon 
              style={{ marginBottom: 16 }} 
            />
            
            <Form.Item label="启用Stream模式" name="dingtalk_stream_enabled" valuePropName="checked" tooltip="开启后使用Stream模式连接钉钉，无需公网IP">
              <Switch checkedChildren="Stream模式" unCheckedChildren="Webhook模式" />
            </Form.Item>

            {watchedStreamEnabled ? (
              <>
                <Form.Item label="钉钉 Client ID" name="dingtalk_client_id" tooltip="从钉钉开放平台获取AppKey">
                  <Input placeholder="输入钉钉AppKey" />
                </Form.Item>
                <Form.Item label="钉钉 Client Secret" name="dingtalk_client_secret" tooltip="从钉钉开放平台获取AppSecret">
                  <Input.Password placeholder="输入钉钉AppSecret (留空表示不修改)" />
                </Form.Item>
              </>
            ) : (
              <>
                <Form.Item label="钉钉 Webhook 地址" name="dingtalk_webhook" tooltip="在钉钉群聊中添加机器人，获取Webhook地址并复制到这里">
                  <Input placeholder="https://oapi.dingtalk.com/robot/send?access_token=xxx" />
                </Form.Item>
                <Form.Item label="钉钉密钥（可选）" name="dingtalk_secret" tooltip="开启机器人安全设置后需要填写密钥">
                  <Input.Password placeholder="SEC开头的密钥（可选）" />
                </Form.Item>
              </>
            )}

            <Divider orientation="left">智能分析配置</Divider>
            <Form.Item label="启用智能提醒" name="enabled" valuePropName="checked">
              <Switch checkedChildren="已启用" unCheckedChildren="已禁用" />
            </Form.Item>

            {watchedEnabled && (
              <>
                <Divider orientation="left">分析维度配置</Divider>
                <Form.Item tooltip="您可以选择启用一项或多项分析维度。">
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    <Checkbox checked={analysisConfig.overdue} onChange={e => setAnalysisConfig({...analysisConfig, overdue: e.target.checked})}>逾期检测</Checkbox>
                    <Checkbox checked={analysisConfig.progress_stalled} onChange={e => setAnalysisConfig({...analysisConfig, progress_stalled: e.target.checked})}>进度落后检测</Checkbox>
                    <Checkbox checked={analysisConfig.dependency_unblocked} onChange={e => setAnalysisConfig({...analysisConfig, dependency_unblocked: e.target.checked})}>依赖解除检测</Checkbox>
                    <Checkbox checked={analysisConfig.team_load} onChange={e => setAnalysisConfig({...analysisConfig, team_load: e.target.checked})}>团队负荷分析</Checkbox>
                    <Checkbox checked={analysisConfig.risk_prediction} onChange={e => setAnalysisConfig({...analysisConfig, risk_prediction: e.target.checked})}>风险预测</Checkbox>
                  </div>
                </Form.Item>

                <Divider orientation="left">高级设置</Divider>
                <Form.Item label="每日提醒上限" name="daily_limit" tooltip="每天最多发送的提醒次数"><InputNumber min={1} max={20} defaultValue={5} style={{ width: 120 }} /></Form.Item>
              </>
            )}

            <Form.Item style={{ marginTop: 24 }}><Space>
              <Button type="primary" htmlType="submit" loading={loadingReminder} icon={<SaveOutlined />}>保存设置</Button>
              <Button onClick={handleTriggerReminder} loading={triggering}>立即提醒</Button>
              <Button onClick={() => handleLoadStats(7)} loading={loadingStats}>查看统计</Button>
            </Space></Form.Item>

            {statsData && (
              <Alert message={`统计报表 (近${statsData.period_days}天)`} description={<div><p>总发送: {statsData.total} 条</p><p>已读: {statsData.read_count} 条 ({statsData.read_rate}%)</p></div>} type="info" style={{ marginTop: 16 }} />
            )}
          </Form>
        </Card>
      ),
    },
    {
      key: 'about',
      label: '关于',
      children: (
        <Card bordered={false}>
          <div style={{ textAlign: 'center', padding: 24 }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#1890ff', marginBottom: 8 }}>TaskTree</div>
            <div style={{ color: '#666', marginBottom: 16 }}>任务树 - 让项目管理更直观</div>
            <Divider />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, maxWidth: 300, margin: '0 auto', textAlign: 'left' }}>
              <span style={{ color: '#999' }}>版本</span><span>1.0.0</span>
              <span style={{ color: '#999' }}>技术栈</span><span>React + FastAPI</span>
              <span style={{ color: '#999' }}>数据库</span><span>SQLite</span>
              <span style={{ color: '#999' }}>UI 框架</span><span>Ant Design 5</span>
            </div>
          </div>
        </Card>
      ),
    },
  ];

  return (
    <div className="page-container" style={{ maxWidth: 800, margin: '0 auto', padding: '32px 24px' }}>
      <Helmet><title>TaskTree 设置 - Nexus</title></Helmet>
      <h2 style={{
        fontSize: 22, fontWeight: 600, marginBottom: 24,
        color: 'var(--color-ink)',
        fontFamily: 'var(--font-heading)',
        letterSpacing: '-0.02em',
      }}>
        TaskTree 设置
      </h2>
      <Card bordered={false} style={{
        background: 'var(--color-surface)',
        borderRadius: 'var(--radius-card)',
        border: '1px solid var(--color-border)',
      }}>
        <Tabs items={tabItems} defaultActiveKey="reminder" />
      </Card>
    </div>
  );
}
