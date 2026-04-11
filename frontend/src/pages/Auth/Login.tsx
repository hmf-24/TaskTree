import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Form, Input, Button, Card, message } from 'antd';
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
      if (res.code === 200) {
        const token = res.data.access_token;
        // 获取用户信息
        const userRes = await authAPI.getCurrentUser();
        if (userRes.code === 200) {
          const user = userRes.data;
          setAuth({ id: user.id, email: user.email, nickname: user.nickname, avatar: user.avatar }, token);
        } else {
          setAuth({ id: 0, email: values.email, nickname: '' }, token);
        }
        message.success('登录成功');
        navigate('/');
      } else {
        message.error(res.message || '登录失败');
      }
    } catch (error: any) {
      message.error(error.message || '登录失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <Card className="w-96">
        <h1 className="text-2xl font-bold text-center mb-6">TaskTree 登录</h1>
        <Form onFinish={onFinish} size="large">
          <Form.Item name="email" rules={[{ required: true, message: '请输入邮箱' }]}>
            <Input prefix={<UserOutlined />} placeholder="邮箱" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              登录
            </Button>
          </Form.Item>
          <div className="text-center">
            还没有账号？<a href="/auth/register">立即注册</a>
          </div>
        </Form>
      </Card>
    </div>
  );
}