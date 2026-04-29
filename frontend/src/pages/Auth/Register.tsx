import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Form, Input, Button, message } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined } from '@ant-design/icons';
import { authAPI } from '../../api';

export default function Register() {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const onFinish = async (values: { email: string; password: string; nickname: string }) => {
    setLoading(true);
    try {
      const res = await authAPI.register(values);
      if (res.code === 201) {
        message.success('注册成功，请登录');
        navigate('/auth/login');
      } else {
        message.error(res.message || '注册失败');
      }
    } catch (error: any) {
      message.error(error.message || '注册失败');
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
              fontSize: 20, color: '#fff', fontWeight: 700,
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
            创建账号
          </h1>
          <p style={{
            color: 'var(--color-ink-secondary)', fontSize: 13, margin: '8px 0 0',
            lineHeight: 1.5,
          }}>
            注册 TaskTree，开始高效协作
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
              prefix={<MailOutlined style={{ color: 'var(--color-ink-tertiary)' }} />}
              placeholder="邮箱地址"
              style={{ height: 42 }}
            />
          </Form.Item>
          <Form.Item name="nickname" rules={[{ required: true, message: '请输入昵称' }]}>
            <Input
              prefix={<UserOutlined style={{ color: 'var(--color-ink-tertiary)' }} />}
              placeholder="昵称"
              style={{ height: 42 }}
            />
          </Form.Item>
          <Form.Item
            name="password"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 8, message: '密码至少8位' },
              {
                pattern: /^(?=.*[A-Za-z])(?=.*\d).+$/,
                message: '密码必须包含字母和数字',
              },
            ]}
          >
            <Input.Password
              prefix={<LockOutlined style={{ color: 'var(--color-ink-tertiary)' }} />}
              placeholder="密码（至少8位，包含字母和数字）"
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
              注册
            </Button>
          </Form.Item>
          <div style={{
            textAlign: 'center',
            color: 'var(--color-ink-secondary)',
            fontSize: 13,
          }}>
            已有账号？
            <Link
              to="/auth/login"
              style={{
                fontWeight: 600,
                color: 'var(--color-ink)',
                marginLeft: 4,
                textDecoration: 'none',
                borderBottom: '1px solid var(--color-border-strong)',
                transition: 'border-color 0.15s var(--ease-smooth)',
              }}
            >
              立即登录
            </Link>
          </div>
        </Form>
      </div>
    </div>
  );
}
