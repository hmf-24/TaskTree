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
            创建账号
          </h1>
          <p style={{ color: '#888', fontSize: 14, margin: '8px 0 0' }}>
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
              prefix={<MailOutlined style={{ color: '#bfbfbf' }} />}
              placeholder="邮箱地址"
              style={{ borderRadius: 10, height: 46 }}
            />
          </Form.Item>
          <Form.Item name="nickname" rules={[{ required: true, message: '请输入昵称' }]}>
            <Input
              prefix={<UserOutlined style={{ color: '#bfbfbf' }} />}
              placeholder="昵称"
              style={{ borderRadius: 10, height: 46 }}
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
              prefix={<LockOutlined style={{ color: '#bfbfbf' }} />}
              placeholder="密码（至少8位，包含字母和数字）"
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
              注册
            </Button>
          </Form.Item>
          <div style={{ textAlign: 'center', color: '#888', fontSize: 14 }}>
            已有账号？<Link to="/auth/login" style={{ fontWeight: 600 }}>立即登录</Link>
          </div>
        </Form>
      </div>
    </div>
  );
}
