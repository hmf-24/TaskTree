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
  Select,
  Checkbox,
  Upload,
} from 'antd';
import {
  UserOutlined,
  LockOutlined,
  SaveOutlined,
  BellOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import type { UploadProps } from 'antd';
import { Helmet } from 'react-helmet-async';
import { authAPI, reminderSettingsAPI } from '../../api';
import { useAuthStore } from '../../stores/auth';

const LLM_PROVIDERS: Record<string, any> = {
  minimax: {
    name: 'Minimax',
    models: [
      { value: 'MiniMax-M2.7', label: 'MiniMax-M2.7' },
      { value: 'MiniMax-M2', label: 'MiniMax-M2' },
      { value: 'MiniMax-M1.5', label: 'MiniMax-M1.5' },
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
  custom: {
    name: '自定义',
    models: [],
    apiKeyPlaceholder: '输入API Key',
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
  const [triggering, setTriggering] = useState(false);
  const [loadingStats, setLoadingStats] = useState(false);
  const [statsData, setStatsData] = useState<any>(null);
  const [testingConn, setTestingConn] = useState(false);
  const [connResult, setConnResult] = useState<{ success: boolean; msg: string; detail?: any } | null>(null);
  const [uploading, setUploading] = useState(false);
  // 分析维度用独立 state，避免 setFieldsValue 嵌套路径问题
  const [analysisConfig, setAnalysisConfig] = useState({
    overdue: true, progress_stalled: true, dependency_unblocked: true, team_load: true, risk_prediction: true,
  });

  const watchedProvider = Form.useWatch('llm_provider', reminderForm);

  useEffect(() => {
    if (user) {
      profileForm.setFieldsValue({ email: user.email, nickname: user.nickname || '' });
    }
  }, [user, profileForm]);

  // 加载设置时把 analysis_config 拆开为顶层字段
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
            dingtalk_webhook: res.data.dingtalk_webhook,
            dingtalk_secret: res.data.dingtalk_secret,
            llm_provider: res.data.llm_provider === 'custom' ? 'custom' : 'minimax',
            llm_api_key: res.data.llm_api_key,
            llm_model: res.data.llm_model,
            llm_group_id: res.data.llm_group_id,
            daily_limit: res.data.daily_limit || 5,
          });
        }
      } catch (error) {
        console.error('加载提醒设置失败:', error);
      }
    };
    loadReminderSettings();
  }, [reminderForm]);

  const handleSaveProfile = async (values: any) => {
    setSaving(true);
    try {
      const res = await authAPI.updateUser({ nickname: values.nickname, avatar: values.avatar });
      if (res.code === 200) {
        message.success('个人资料已更新');
        if (token) {
          setAuth({ id: user!.id, email: user!.email, nickname: values.nickname, avatar: values.avatar || user?.avatar }, token);
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

  const handleChangePassword = async (values: any) => {
    if (values.new_password !== values.confirm_password) { message.error('两次输入的新密码不一致'); return; }
    setChangingPassword(true);
    try {
      const res = await authAPI.changePassword({ old_password: values.old_password, new_password: values.new_password });
      if (res.code === 200) { message.success('密码修改成功'); passwordForm.resetFields(); }
      else { message.error(res.message || '修改失败'); }
    } catch (error: any) { message.error(error.message || '修改失败'); }
    finally { setChangingPassword(false); }
  };

  const handleSaveReminder = async (values: any) => {
    setLoadingReminder(true);
    try {
      const res = await reminderSettingsAPI.updateSettings({
        enabled: values.enabled,
        dingtalk_webhook: values.dingtalk_webhook,
        dingtalk_secret: values.dingtalk_secret,
        llm_provider: values.llm_provider,
        llm_api_key: values.llm_api_key,
        llm_model: values.llm_model,
        llm_group_id: values.llm_group_id,
        daily_limit: values.daily_limit || 5,
        analysis_config: analysisConfig,
      });
      if (res.code === 200) { message.success('智能提醒设置已保存'); }
      else { message.error(res.message || '保存失败'); }
    } catch (error: any) { message.error(error.message || '保存失败'); }
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

  const handleTestConnection = async () => {
    const values = reminderForm.getFieldsValue();
    if (!values.llm_api_key) { message.error('请先输入 API Key'); return; }
    if (!values.llm_model) { message.error('请先选择或输入模型名称'); return; }
    setTestingConn(true);
    setConnResult(null);
    try {
      const res = await reminderSettingsAPI.testConnection({
        provider: values.llm_provider || 'minimax',
        api_key: values.llm_api_key,
        model: values.llm_model,
        group_id: values.llm_group_id,
      });
      if (res.code === 200 && res.data?.success) {
        setConnResult({ success: true, msg: `连接成功，耗时 ${res.data.response_time_ms}ms`, detail: res.data });
      } else {
        setConnResult({ success: false, msg: res.message || res.data?.error || '连接失败' });
      }
    } catch (error: any) { setConnResult({ success: false, msg: error.message || '连接失败' }); }
    finally { setTestingConn(false); }
  };

  const handleAvatarUpload: UploadProps['customRequest'] = async (options) => {
    const { file, onSuccess, onError } = options;
    
    // 检查文件类型
    const isImage = (file as File).type.startsWith('image/');
    if (!isImage) {
      message.error('只能上传图片文件！');
      onError?.(new Error('只能上传图片文件'));
      return;
    }

    // 检查图片尺寸比例
    const img = new Image();
    const reader = new FileReader();
    
    reader.onload = (e) => {
      img.src = e.target?.result as string;
      img.onload = async () => {
        const ratio = img.width / img.height;
        if (Math.abs(ratio - 1) > 0.1) {
          message.warning('建议上传1:1比例的图片以获得最佳显示效果');
        }

        // 上传文件
        setUploading(true);
        try {
          const formData = new FormData();
          formData.append('file', file as File);

          const response = await fetch('/api/v1/tasktree/attachments/upload', {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${token}`,
            },
            body: formData,
          });

          const result = await response.json();
          
          if (result.code === 200 && result.data) {
            const avatarUrl = result.data.url;
            profileForm.setFieldsValue({ avatar: avatarUrl });
            message.success('头像上传成功！');
            onSuccess?.(result.data);
          } else {
            message.error(result.message || '上传失败');
            onError?.(new Error(result.message || '上传失败'));
          }
        } catch (error: any) {
          message.error(error.message || '上传失败');
          onError?.(error);
        } finally {
          setUploading(false);
        }
      };
    };
    
    reader.readAsDataURL(file as File);
  };

  const isCustomProvider = watchedProvider === 'custom';
  const currentProvider = LLM_PROVIDERS[watchedProvider] || LLM_PROVIDERS.minimax;

  const tabItems = [
    {
      key: 'profile',
      label: '个人资料',
      children: (
        <Card bordered={false}>
          <div style={{ textAlign: 'center', marginBottom: 24 }}>
            <Avatar size={80} icon={<UserOutlined />} src={user?.avatar} style={{ marginBottom: 12 }} />
            <div style={{ fontSize: 18, fontWeight: 600 }}>{user?.nickname || user?.email}</div>
            <div style={{ color: '#999', fontSize: 13 }}>{user?.email}</div>
          </div>
          <Form form={profileForm} layout="vertical" onFinish={handleSaveProfile} style={{ maxWidth: 400, margin: '0 auto' }}>
            <Form.Item label="邮箱" name="email"><Input disabled prefix={<UserOutlined />} /></Form.Item>
            <Form.Item label="昵称" name="nickname" rules={[{ required: true, message: '请输入昵称' }]}><Input placeholder="请输入昵称" prefix={<UserOutlined />} /></Form.Item>
            <Form.Item label="头像" name="avatar" extra="建议上传1:1比例的图片，支持JPG、PNG等格式">
              <Input.Group compact style={{ display: 'flex', gap: 8 }}>
                <Input placeholder="头像URL（可选）" style={{ flex: 1 }} />
                <Upload
                  showUploadList={false}
                  customRequest={handleAvatarUpload}
                  accept="image/*"
                >
                  <Button icon={<UploadOutlined />} loading={uploading}>
                    {uploading ? '上传中...' : '上传图片'}
                  </Button>
                </Upload>
              </Input.Group>
            </Form.Item>
            <Form.Item><Button type="primary" htmlType="submit" loading={saving} icon={<SaveOutlined />} block>保存修改</Button></Form.Item>
          </Form>
        </Card>
      ),
    },
    {
      key: 'password',
      label: '修改密码',
      children: (
        <Card bordered={false}>
          <Form form={passwordForm} layout="vertical" onFinish={handleChangePassword} style={{ maxWidth: 400, margin: '0 auto' }}>
            <Form.Item label="当前密码" name="old_password" rules={[{ required: true, message: '请输入当前密码' }]}><Input.Password prefix={<LockOutlined />} placeholder="请输入当前密码" /></Form.Item>
            <Form.Item label="新密码" name="new_password" rules={[{ required: true, message: '请输入新密码' }, { min: 8, message: '密码至少8位' }, { pattern: /^(?=.*[A-Za-z])(?=.*\d).+$/, message: '密码必须包含字母和数字' }]}><Input.Password prefix={<LockOutlined />} placeholder="请输入新密码" /></Form.Item>
            <Form.Item label="确认新密码" name="confirm_password" dependencies={['new_password']} rules={[{ required: true, message: '请再次输入新密码' }, ({ getFieldValue }) => ({ validator: (_, value) => (!value || getFieldValue('new_password') === value ? Promise.resolve() : Promise.reject(new Error('两次密码不一致'))) })]}><Input.Password prefix={<LockOutlined />} placeholder="请再次输入新密码" /></Form.Item>
            <Form.Item><Button type="primary" htmlType="submit" loading={changingPassword} icon={<LockOutlined />} block>修改密码</Button></Form.Item>
          </Form>
        </Card>
      ),
    },
    {
      key: 'reminder',
      label: <span><BellOutlined /> 智能提醒</span>,
      children: (
        <Card bordered={false}>
          <Alert message="智能提醒说明" description="开启智能提醒后，系统会定期使用大模型分析您的任务，并通过钉钉发送个性化提醒通知。" type="info" showIcon style={{ marginBottom: 24 }} />
          <Form form={reminderForm} layout="vertical" onFinish={handleSaveReminder} style={{ maxWidth: 600 }}>
            <Form.Item label="启用智能提醒" name="enabled" valuePropName="checked">
              <Switch checkedChildren="已启用" unCheckedChildren="已禁用" />
            </Form.Item>

            {Form.useWatch('enabled', reminderForm) && (
              <>
                <Divider orientation="left">基础设置</Divider>
                <Form.Item label="钉钉 Webhook 地址" name="dingtalk_webhook" tooltip="在钉钉群聊中添加机器人，获取Webhook地址并复制到这里"><Input placeholder="https://oapi.dingtalk.com/robot/send?access_token=xxx" /></Form.Item>
                <Form.Item label="钉钉密钥（可选）" name="dingtalk_secret" tooltip="开启机器人安全设置后需要填写密钥"><Input.Password placeholder="SEC开头的密钥（可选）" /></Form.Item>

                <Divider orientation="left">大模型配置</Divider>
                <Form.Item label="大模型提供商" name="llm_provider" tooltip="选择要使用的大模型服务商">
                  <Select placeholder="选择提供商" onChange={() => { reminderForm.setFieldsValue({ llm_model: undefined }); setConnResult(null); }}>
                    {Object.entries(LLM_PROVIDERS).map(([key, value]) => <Select.Option key={key} value={key}>{value.name}</Select.Option>)}
                  </Select>
                </Form.Item>
                <Form.Item label="模型选择" name="llm_model" tooltip="选择或输入模型名称">
                  {isCustomProvider
                    ? <Input placeholder="请输入模型名称，如 MiniMax-M2.7" />
                    : <Select placeholder="选择模型" allowClear>{currentProvider.models.map((m: any) => <Select.Option key={m.value} value={m.value}>{m.label}</Select.Option>)}</Select>}
                </Form.Item>
                <Form.Item label="API Key" name="llm_api_key" tooltip="从对应平台获取API Key"><Input.Password placeholder={currentProvider.apiKeyPlaceholder} /></Form.Item>
                {(watchedProvider === 'minimax' || isCustomProvider) && (
                  <Form.Item label="Group ID（可选）" name="llm_group_id" tooltip="从Minimax开放平台获取Group ID"><Input placeholder="输入Group ID（可选）" /></Form.Item>
                )}

                {connResult && (
                  <Alert message={connResult.success ? '连接成功' : '连接失败'} description={connResult.success ? `${connResult.msg}\n响应示例：${connResult.detail?.sample_output || ''}` : connResult.msg} type={connResult.success ? 'success' : 'error'} showIcon icon={connResult.success ? <CheckCircleOutlined /> : <CloseCircleOutlined />} style={{ marginBottom: 16 }} />
                )}
                <Form.Item>
                  <Button onClick={handleTestConnection} loading={testingConn} icon={testingConn ? <LoadingOutlined /> : undefined}>{testingConn ? '测试中...' : '测试连通性'}</Button>
                </Form.Item>

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
    <div className="p-6">
      <Helmet><title>设置 - TaskTree</title></Helmet>
      <h1 className="text-2xl font-bold mb-6">设置</h1>
      <div style={{ maxWidth: 640, margin: '0 auto' }}><Tabs items={tabItems} defaultActiveKey="profile" /></div>
    </div>
  );
}