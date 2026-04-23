import { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Input,
  Button,
  Avatar,
  Divider,
  message,
  Tabs,
  Switch,
  InputNumber,
  Alert,
  Space,
  Tag,
  Select,
} from 'antd';
import {
  UserOutlined,
  LockOutlined,
  SaveOutlined,
  BellOutlined,
} from '@ant-design/icons';
import { Helmet } from 'react-helmet-async';
import { authAPI, reminderSettingsAPI } from '../../api';
import { useAuthStore } from '../../stores/auth';

// 大模型提供商配置
const LLM_PROVIDERS = {
  minimax: {
    name: 'Minimax',
    models: [
      { value: 'abab6.5s-chat', label: 'abab6.5s-chat' },
      { value: 'abab6.5g-chat', label: 'abab6.5g-chat' },
    ],
    apiKeyPlaceholder: '输入您的Minimax API Key',
    groupIdShow: true,
  },
  openai: {
    name: 'OpenAI',
    models: [
      { value: 'gpt-4o', label: 'GPT-4o' },
      { value: 'gpt-4o-mini', label: 'GPT-4o-mini' },
      { value: 'gpt-4-turbo', label: 'GPT-4-turbo' },
    ],
    apiKeyPlaceholder: '输入您的OpenAI API Key (sk-...)',
    groupIdShow: false,
  },
  anthropic: {
    name: 'Anthropic',
    models: [
      { value: 'claude-sonnet-4-20250514', label: 'Claude Sonnet 4' },
      { value: 'claude-3-opus-20240229', label: 'Claude 3 Opus' },
      { value: 'claude-3-haiku-20240307', label: 'Claude 3 Haiku' },
    ],
    apiKeyPlaceholder: '输入您的Anthropic API Key (sk-ant-...)',
    groupIdShow: false,
  },
};

export default function Settings() {
  const { user, setAuth, token } = useAuthStore();
  const [profileForm] = Form.useForm();
  const [passwordForm] = Form.useForm();
  const [reminderForm] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);
  const [loadingReminder, setLoadingReminder] = useState(false);
  const [reminderSettings, setReminderSettings] = useState<any>(null);
  const [triggering, setTriggering] = useState(false);
  const [loadingStats, setLoadingStats] = useState(false);
  const [statsData, setStatsData] = useState<any>(null);

  // 监听 llm_provider 字段变化以联动模型列表
  const watchedProvider = Form.useWatch('llm_provider', reminderForm);

  useEffect(() => {
    if (user) {
      profileForm.setFieldsValue({
        email: user.email,
        nickname: user.nickname || '',
      });
    }
  }, [user, profileForm]);

  // ---- 加载智能提醒设置 ----
  useEffect(() => {
    const loadReminderSettings = async () => {
      try {
        const res = await reminderSettingsAPI.getSettings();
        if (res.code === 200 && res.data) {
          setReminderSettings(res.data);
          reminderForm.setFieldsValue({
            enabled: res.data.enabled,
            dingtalk_webhook: res.data.dingtalk_webhook,
            dingtalk_secret: res.data.dingtalk_secret,
            llm_provider: res.data.llm_provider || 'minmax',
            llm_api_key: res.data.llm_api_key,
            llm_model: res.data.llm_model,
            llm_group_id: res.data.llm_group_id,
            daily_limit: res.data.daily_limit || 5,
            rules: res.data.rules,
          });
        }
      } catch (error) {
        console.error('加载提醒设置失败:', error);
      }
    };
    loadReminderSettings();
  }, [reminderForm]);

  // ---- 个人资料 ----
  const handleSaveProfile = async (values: any) => {
    setSaving(true);
    try {
      const res = await authAPI.updateUser({ nickname: values.nickname, avatar: values.avatar });
      if (res.code === 200) {
        message.success('个人资料已更新');
        if (token) {
          setAuth(
            {
              id: user!.id,
              email: user!.email,
              nickname: values.nickname,
              avatar: values.avatar || user?.avatar,
            },
            token
          );
        }
      } else {
        message.error(res.message || '更新失败');
      }
    } catch (error: any) {
      message.error(error.message || '更新失败');
    } finally {
      setSaving(false);
    }
  };

  // ---- 修改密码 ----
  const handleChangePassword = async (values: any) => {
    if (values.new_password !== values.confirm_password) {
      message.error('两次输入的新密码不一致');
      return;
    }
    setChangingPassword(true);
    try {
      const res = await authAPI.changePassword({
        old_password: values.old_password,
        new_password: values.new_password,
      });
      if (res.code === 200) {
        message.success('密码修改成功，请牢记新密码');
        passwordForm.resetFields();
      } else {
        message.error(res.message || '修改失败');
      }
    } catch (error: any) {
      message.error(error.message || '修改失败');
    } finally {
      setChangingPassword(false);
    }
  };

  // ---- 保存智能提醒设置 ----
  const handleSaveReminder = async (values: any) => {
    setLoadingReminder(true);
    try {
      const data = {
        enabled: values.enabled,
        dingtalk_webhook: values.dingtalk_webhook,
        dingtalk_secret: values.dingtalk_secret,
        llm_provider: values.llm_provider,
        llm_api_key: values.llm_api_key,
        llm_model: values.llm_model,
        llm_group_id: values.llm_group_id,
        daily_limit: values.daily_limit || 5,
        rules: values.rules,
      };
      const res = await reminderSettingsAPI.updateSettings(data);
      if (res.code === 200) {
        message.success('智能提醒设置已保存');
        setReminderSettings(res.data);
      } else {
        message.error(res.message || '保存失败');
      }
    } catch (error: any) {
      message.error(error.message || '保存失败');
    } finally {
      setLoadingReminder(false);
    }
  };

  // ---- 手动触发提醒 ----
  const handleTriggerReminder = async () => {
    setTriggering(true);
    try {
      const res = await reminderSettingsAPI.trigger();
      if (res.code === 200) {
        message.success('提醒已发送');
      } else {
        message.error(res.message || '发送失败');
      }
    } catch (error: any) {
      message.error(error.message || '发送失败');
    } finally {
      setTriggering(false);
    }
  };

  // ---- 加载统计 ----
  const handleLoadStats = async (days: number = 7) => {
    setLoadingStats(true);
    try {
      const res = await reminderSettingsAPI.getStats(days);
      if (res.code === 200) {
        setStatsData(res.data);
      }
    } catch (error) {
      console.error('加载统计失败:', error);
    } finally {
      setLoadingStats(false);
    }
  };

  const tabItems = [
    {
      key: 'profile',
      label: '个人资料',
      children: (
        <Card bordered={false}>
          <div style={{ textAlign: 'center', marginBottom: 24 }}>
            <Avatar
              size={80}
              icon={<UserOutlined />}
              src={user?.avatar}
              style={{ marginBottom: 12 }}
            />
            <div style={{ fontSize: 18, fontWeight: 600 }}>{user?.nickname || user?.email}</div>
            <div style={{ color: '#999', fontSize: 13 }}>{user?.email}</div>
          </div>

          <Form
            form={profileForm}
            layout="vertical"
            onFinish={handleSaveProfile}
            style={{ maxWidth: 400, margin: '0 auto' }}
          >
            <Form.Item label="邮箱" name="email">
              <Input disabled prefix={<UserOutlined />} />
            </Form.Item>
            <Form.Item
              label="昵称"
              name="nickname"
              rules={[{ required: true, message: '请输入昵称' }]}
            >
              <Input placeholder="请输入昵称" prefix={<UserOutlined />} />
            </Form.Item>
            <Form.Item label="头像 URL" name="avatar">
              <Input placeholder="请输入头像 URL（可选）" />
            </Form.Item>
            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                loading={saving}
                icon={<SaveOutlined />}
                block
              >
                保存修改
              </Button>
            </Form.Item>
          </Form>
        </Card>
      ),
    },
    {
      key: 'password',
      label: '修改密码',
      children: (
        <Card bordered={false}>
          <Form
            form={passwordForm}
            layout="vertical"
            onFinish={handleChangePassword}
            style={{ maxWidth: 400, margin: '0 auto' }}
          >
            <Form.Item
              label="当前密码"
              name="old_password"
              rules={[{ required: true, message: '请输入当前密码' }]}
            >
              <Input.Password prefix={<LockOutlined />} placeholder="请输入当前密码" />
            </Form.Item>
            <Form.Item
              label="新密码"
              name="new_password"
              rules={[
                { required: true, message: '请输入新密码' },
                { min: 8, message: '密码至少8位' },
                {
                  pattern: /^(?=.*[A-Za-z])(?=.*\d).+$/,
                  message: '密码必须包含字母和数字',
                },
              ]}
            >
              <Input.Password prefix={<LockOutlined />} placeholder="请输入新密码" />
            </Form.Item>
            <Form.Item
              label="确认新密码"
              name="confirm_password"
              dependencies={['new_password']}
              rules={[
                { required: true, message: '请再次输入新密码' },
                ({ getFieldValue }) => ({
                  validator(_, value) {
                    if (!value || getFieldValue('new_password') === value) {
                      return Promise.resolve();
                    }
                    return Promise.reject(new Error('两次密码不一致'));
                  },
                }),
              ]}
            >
              <Input.Password prefix={<LockOutlined />} placeholder="请再次输入新密码" />
            </Form.Item>
            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                loading={changingPassword}
                icon={<LockOutlined />}
                block
              >
                修改密码
              </Button>
            </Form.Item>
          </Form>
        </Card>
      ),
    },
    {
      key: 'reminder',
      label: (
        <span>
          <BellOutlined /> 智能提醒
        </span>
      ),
      children: (
        <Card bordered={false}>
          <Alert
            message="智能提醒说明"
            description="开启智能提醒后，系统会定期使用大模型分析您的任务，并通过钉钉发送个性化提醒通知。您可以自定义提醒规则和每日上限。"
            type="info"
            showIcon
            style={{ marginBottom: 24 }}
          />

          <Form
            form={reminderForm}
            layout="vertical"
            onFinish={handleSaveReminder}
            style={{ maxWidth: 600 }}
          >
            <Divider orientation="left">基础设置</Divider>

            <Form.Item label="启用智能提醒" name="enabled" valuePropName="checked">
              <Switch checkedChildren="已启用" unCheckedChildren="已禁用" />
            </Form.Item>

            <Form.Item
              label="钉钉 Webhook 地址"
              name="dingtalk_webhook"
              tooltip="在钉钉群聊中添加机器人，获取Webhook地址并复制到这里"
            >
              <Input placeholder="https://oapi.dingtalk.com/robot/send?access_token=xxx" />
            </Form.Item>

            <Form.Item
              label="钉钉密钥（可选）"
              name="dingtalk_secret"
              tooltip="开启机器人安全设置后需要填写密钥"
            >
              <Input.Password placeholder="SEC开头的密钥（可选）" />
            </Form.Item>

            <Divider orientation="left">大模型配置</Divider>

            <Form.Item
              label="大模型提供商"
              name="llm_provider"
              tooltip="选择要使用的大模型服务商"
            >
              <Select
                placeholder="选择提供商"
                onChange={() => {
                  reminderForm.setFieldsValue({ llm_model: undefined });
                }}
              >
                {Object.entries(LLM_PROVIDERS).map(([key, value]) => (
                  <Select.Option key={key} value={key}>
                    {value.name}
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              label="模型选择"
              name="llm_model"
              tooltip="选择具体模型版本"
            >
              <Select placeholder="选择模型" allowClear>
                {watchedProvider &&
                  (LLM_PROVIDERS as any)[watchedProvider]?.models.map((m: any) => (
                    <Select.Option key={m.value} value={m.value}>
                      {m.label}
                    </Select.Option>
                  ))}
              </Select>
            </Form.Item>

            <Form.Item
              label="API Key"
              name="llm_api_key"
              tooltip="从对应平台获取API Key"
            >
              <Input.Password
                placeholder={
                  (watchedProvider && (LLM_PROVIDERS as any)[watchedProvider]?.apiKeyPlaceholder) ||
                  '输入API Key'
                }
              />
            </Form.Item>

            {watchedProvider === 'minmax' && (
              <Form.Item
                label="Group ID（Minimax专属）"
                name="llm_group_id"
                tooltip="从Minimax开放平台获取Group ID（可选，部分模型需要）"
              >
                <Input placeholder="输入Group ID（可选）" />
              </Form.Item>
            )}

            <Divider orientation="left">分析维度配置</Divider>

            <Form.Item label="逾期检测" name={['analysis_config', 'overdue']} valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item label="进度落后检测" name={['analysis_config', 'progress_stalled']} valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item label="依赖解除检测" name={['analysis_config', 'dependency_unblocked']} valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item label="团队负荷分析" name={['analysis_config', 'team_load']} valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item label="风险预测" name={['analysis_config', 'risk_prediction']} valuePropName="checked">
              <Switch />
            </Form.Item>

            <Divider orientation="left">高级设置</Divider>

            <Form.Item label="每日提醒上限" name="daily_limit" tooltip="每天最多发送的提醒次数">
              <InputNumber min={1} max={20} defaultValue={5} style={{ width: 120 }} />
            </Form.Item>

            <Form.Item
              label="自定义规则（JSON）"
              name="rules"
              tooltip="高级用户可自定义提醒规则，JSON格式"
            >
              <Input.TextArea
                rows={6}
                placeholder={`[
  {
    "id": "overdue",
    "name": "任务逾期提醒",
    "enabled": true,
    "condition": "overdue",
    "hours_before": 0
  },
  {
    "id": "due_soon",
    "name": "即将到期提醒",
    "enabled": true,
    "condition": "due_soon",
    "hours_before": 24
  }
]`}
                style={{ fontFamily: 'monospace' }}
              />
            </Form.Item>

            <Form.Item>
              <Space>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={loadingReminder}
                  icon={<SaveOutlined />}
                >
                  保存设置
                </Button>
                <Button
                  onClick={handleTriggerReminder}
                  loading={triggering}
                >
                  立即提醒
                </Button>
                <Button onClick={() => handleLoadStats(7)} loading={loadingStats}>
                  查看统计
                </Button>
              </Space>
            </Form.Item>

            {statsData && (
              <Alert
                message={`统计报表 (近${statsData.period_days}天)`}
                description={
                  <div>
                    <p>总发送: {statsData.total} 条</p>
                    <p>已读: {statsData.read_count} 条 ({statsData.read_rate}%)</p>
                  </div>
                }
                type="info"
                style={{ marginTop: 16 }}
              />
            )}

            {reminderSettings && (
              <>
                <Divider />
                <div style={{ color: '#666', fontSize: 13 }}>
                  <p>当前状态：{reminderSettings.enabled ? '已启用' : '已禁用'}</p>
                  <p>
                    今日已发送：<Tag color="blue">{reminderSettings.today_count || 0}</Tag> 条
                  </p>
                </div>
              </>
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
            <div style={{ fontSize: 28, fontWeight: 700, color: '#1890ff', marginBottom: 8 }}>
              TaskTree
            </div>
            <div style={{ color: '#666', marginBottom: 16 }}>任务树 - 让项目管理更直观</div>
            <Divider />
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: 12,
                maxWidth: 300,
                margin: '0 auto',
                textAlign: 'left',
              }}
            >
              <span style={{ color: '#999' }}>版本</span>
              <span>1.0.0</span>
              <span style={{ color: '#999' }}>技术栈</span>
              <span>React + FastAPI</span>
              <span style={{ color: '#999' }}>数据库</span>
              <span>SQLite</span>
              <span style={{ color: '#999' }}>UI 框架</span>
              <span>Ant Design 5</span>
            </div>
          </div>
        </Card>
      ),
    },
  ];

  return (
    <div className="p-6">
      <Helmet><title>设置 - TaskTree</title></Helmet>
      <h1 className="text-2xl font-bold mb-6">设置</h1>
      <div style={{ maxWidth: 640, margin: '0 auto' }}>
        <Tabs items={tabItems} defaultActiveKey="profile" />
      </div>
    </div>
  );
}
