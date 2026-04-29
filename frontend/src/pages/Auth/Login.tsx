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
      minHeight: '100dvh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'transparent',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* 移除固定颜色的环境光，因为全局已经有风景背景图 */}

      <div
        className="glass-panel"
        style={{
          width: 400,
          padding: '44px 36px 32px',
          position: 'relative',
          zIndex: 1,
          animation: 'fadeSlideUp 0.5s var(--ease-smooth)',
        }}
      >
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{
            width: 44, height: 44, borderRadius: 'var(--radius-card)',
            background: 'var(--color-brand)',
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            marginBottom: 16,
          }}>
            <span style={{
              fontSize: 20, color: '#000', fontWeight: 700,
              fontFamily: 'var(--font-sans)',
              letterSpacing: '-0.02em',
            }}>T</span>
          </div>
          <h1 style={{
            fontSize: 22, fontWeight: 600, margin: 0,
            color: 'var(--color-ink)',
            letterSpacing: '-0.02em',
            fontFamily: 'var(--font-sans)',
          }}>
            欢迎回来
          </h1>
          <p style={{
            color: 'var(--color-ink-secondary)', fontSize: 13, margin: '8px 0 0',
            lineHeight: 1.5,
          }}>
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
              prefix={<UserOutlined style={{ color: 'var(--color-ink-tertiary)' }} />}
              placeholder="邮箱地址"
              style={{ height: 42 }}
            />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password
              prefix={<LockOutlined style={{ color: 'var(--color-ink-tertiary)' }} />}
              placeholder="密码"
              style={{ height: 42 }}
            />
          </Form.Item>
          <Form.Item style={{ marginBottom: 16 }}>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
              style={{
                height: 42, fontWeight: 600, fontSize: 14,
              }}
            >
              登录
            </Button>
          </Form.Item>
          <div style={{
            textAlign: 'center',
            color: 'var(--color-ink-secondary)',
            fontSize: 13,
          }}>
            还没有账号？
            <Link
              to="/auth/register"
              style={{
                fontWeight: 600,
                color: 'var(--color-ink)',
                marginLeft: 4,
                textDecoration: 'none',
                borderBottom: '1px solid var(--color-border-strong)',
                transition: 'border-color 0.15s var(--ease-smooth)',
              }}
            >
              立即注册
            </Link>
          </div>
        </Form>
      </div>
    </div>
  );
}
