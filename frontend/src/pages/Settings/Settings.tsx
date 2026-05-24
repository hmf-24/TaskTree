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
  Upload,
  Switch,
  Alert,
  Select,
} from 'antd';
import {
  UserOutlined,
  LockOutlined,
  SaveOutlined,
  UploadOutlined,
  ApiOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
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
  const [aiForm] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const [savingAi, setSavingAi] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [testingConn, setTestingConn] = useState(false);
  const [connResult, setConnResult] = useState<{ success: boolean; msg: string; detail?: any } | null>(null);

  const watchedProvider = Form.useWatch('llm_provider', aiForm);

  useEffect(() => {
    if (user) {
      profileForm.setFieldsValue({ email: user.email, nickname: user.nickname || '' });
    }
  }, [user, profileForm]);

  useEffect(() => {
    const loadAISettings = async () => {
      try {
        const res = await reminderSettingsAPI.getSettings();
        if (res.code === 200 && res.data) {
          aiForm.setFieldsValue({
            llm_provider: res.data.llm_provider || 'minimax',
            llm_api_key: res.data.llm_api_key,
            llm_model: res.data.llm_model,
            llm_group_id: res.data.llm_group_id,
          });
        }
      } catch (error) {
        console.error('加载 AI 设置失败:', error);
      }
    };
    loadAISettings();
  }, [aiForm]);

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

  const handleSaveAI = async (values: any) => {
    setSavingAi(true);
    try {
      const res = await reminderSettingsAPI.updateSettings({
        llm_provider: values.llm_provider,
        llm_api_key: values.llm_api_key,
        llm_model: values.llm_model,
        llm_group_id: values.llm_group_id,
      });
      if (res.code === 200) { message.success('AI与通知设置已保存'); }
      else { message.error(res.message || '保存失败'); }
    } catch (error: any) { 
      message.error(error.detail || error.message || '保存失败');
    }
    finally { setSavingAi(false); }
  };

  const handleTestConnection = async () => {
    const values = aiForm.getFieldsValue();
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
    const img = new window.Image();
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
      key: 'ai_config',
      label: <span><ApiOutlined /> AI与通知</span>,
      children: (
        <Card bordered={false}>
          <Alert message="全局 AI 与通知配置" description="这些配置将作为 TaskTree 智能分析、ReadHub 等工具统一使用的底层大模型与通知通道。" type="info" showIcon style={{ marginBottom: 24 }} />
          <Form form={aiForm} layout="vertical" onFinish={handleSaveAI} style={{ maxWidth: 600 }}>
            <Divider orientation="left">大模型配置</Divider>
            <Form.Item label="大模型提供商" name="llm_provider" tooltip="选择要使用的大模型服务商">
              <Select placeholder="选择提供商" onChange={() => { aiForm.setFieldsValue({ llm_model: undefined }); setConnResult(null); }}>
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

            <Form.Item style={{ marginTop: 24 }}>
              <Button type="primary" htmlType="submit" loading={savingAi} icon={<SaveOutlined />}>保存全局 AI 与通知配置</Button>
            </Form.Item>
          </Form>
        </Card>
      ),
    },
  ];

  return (
    <div className="page-container" style={{ maxWidth: 800, margin: '0 auto', padding: '32px 24px' }}>
      <Helmet><title>Nexus 统一设置</title></Helmet>
      <h2 style={{
        fontSize: 22, fontWeight: 600, marginBottom: 24,
        color: 'var(--color-ink)',
        fontFamily: 'var(--font-heading)',
        letterSpacing: '-0.02em',
      }}>
        Nexus 统一设置
      </h2>
      <Card bordered={false} style={{
        background: 'var(--color-surface)',
        borderRadius: 'var(--radius-card)',
        border: '1px solid var(--color-border)',
      }}>
        <Tabs items={tabItems} defaultActiveKey="profile" />
      </Card>
    </div>
  );
}