import { useState, useEffect } from 'react';
import { Card, Form, Input, Button, Avatar, Upload, Divider, message, Tabs, Switch, Modal } from 'antd';
import { UserOutlined, LockOutlined, UploadOutlined, SaveOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import { authAPI } from '../../api';
import { useAuthStore } from '../../stores/auth';

export default function Settings() {
  const { user, setAuth, token } = useAuthStore();
  const [profileForm] = Form.useForm();
  const [passwordForm] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);

  useEffect(() => {
    if (user) {
      profileForm.setFieldsValue({
        email: user.email,
        nickname: user.nickname || '',
      });
    }
  }, [user, profileForm]);

  // ---- 个人资料 ----
  const handleSaveProfile = async (values: any) => {
    setSaving(true);
    try {
      const res = await authAPI.updateUser({ nickname: values.nickname, avatar: values.avatar });
      if (res.code === 200) {
        message.success('个人资料已更新');
        if (token) {
          setAuth(
            { id: user!.id, email: user!.email, nickname: values.nickname, avatar: values.avatar || user?.avatar },
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
                { min: 6, message: '密码至少6位' },
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
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, maxWidth: 300, margin: '0 auto', textAlign: 'left' }}>
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
      <h1 className="text-2xl font-bold mb-6">设置</h1>
      <div style={{ maxWidth: 640, margin: '0 auto' }}>
        <Tabs items={tabItems} defaultActiveKey="profile" />
      </div>
    </div>
  );
}
