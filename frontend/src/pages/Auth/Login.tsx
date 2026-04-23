import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Form, Input, Button, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { authAPI } from '../../api';
import { useAuthStore } from '../../stores/auth';

export default function Login() {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const setAuth = useAuthStore((state) => state.setAuth);

  const onFinish = async (values: { email: string; password: string }) => {
    setLoading(true);
    try {
      const res = await authAPI.login(values);
      if (res.code !== 200) {
        message.error(res.message || '登录失败');
        return;
      }

      const token = res.data.access_token;

      // 先保存 token 到 store，这样后续请求拦截器能正确携带 token
      setAuth({ id: 0, email: values.email, nickname: '' }, token);

      try {
        const userRes = await authAPI.getCurrentUser();
        if (userRes.code === 200) {
          const user = userRes.data;
          setAuth(
            { id: user.id, email: user.email, nickname: user.nickname, avatar: user.avatar },
            token
          );
        }
      } catch {
        // token 已保存，用户信息获取失败不影响登录
        message.warning('登录成功，但无法获取用户信息');
      }

      message.success('登录成功');
      navigate('/');
    } catch (error: any) {
      message.error(error.message || '邮箱或密码错误');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    }}>
      <div style={{
        width: 420,
        background: 'rgba(255, 255, 255, 0.95)',
        backdropFilter: 'blur(20px)',
        borderRadius: 16,
        padding: '48px 40px 36px',
        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.15)',
      }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 36 }}>
          <div style={{
            width: 56, height: 56, borderRadius: 14,
            background: 'linear-gradient(135deg, #667eea, #764ba2)',
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            marginBottom: 16, boxShadow: '0 4px 16px rgba(102, 126, 234, 0.4)',
          }}>
            <span style={{ fontSize: 28, color: '#fff', fontWeight: 700 }}>T</span>
          </div>
          <h1 style={{ fontSize: 26, fontWeight: 700, margin: 0, color: '#1a1a2e' }}>
            欢迎回来
          </h1>
          <p style={{ color: '#888', fontSize: 14, margin: '8px 0 0' }}>
            登录 TaskTree，管理你的任务
          </p>
        </div>

        <Form onFinish={onFinish} size="large" layout="vertical">
          <Form.Item
            name="email"
            rules={[
              { required: true, message: '请输入邮箱' },
              { type: 'email', message: '请输入有效的邮箱' },
            ]}
          >
            <Input
              prefix={<UserOutlined style={{ color: '#bfbfbf' }} />}
              placeholder="邮箱地址"
              style={{ borderRadius: 10, height: 46 }}
            />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password
              prefix={<LockOutlined style={{ color: '#bfbfbf' }} />}
              placeholder="密码"
              style={{ borderRadius: 10, height: 46 }}
            />
          </Form.Item>
          <Form.Item style={{ marginBottom: 16 }}>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
              style={{
                height: 46, borderRadius: 10, fontWeight: 600, fontSize: 15,
                background: 'linear-gradient(135deg, #667eea, #764ba2)',
                border: 'none', boxShadow: '0 4px 16px rgba(102, 126, 234, 0.35)',
              }}
            >
              登录
            </Button>
          </Form.Item>
          <div style={{ textAlign: 'center', color: '#888', fontSize: 14 }}>
            还没有账号？<Link to="/auth/register" style={{ fontWeight: 600 }}>立即注册</Link>
          </div>
        </Form>
      </div>
    </div>
  );
}
