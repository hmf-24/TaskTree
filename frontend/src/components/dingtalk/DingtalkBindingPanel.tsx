/**
 * 钉钉绑定面板组件
 * 
 * 功能：
 * - 显示绑定状态
 * - 绑定钉钉账号
 * - 解除绑定
 * - 发送测试消息
 */
import React, { useState, useEffect } from 'react';
import {
  Card,
  Button,
  Input,
  message,
  Space,
  Typography,
  Divider,
  Tag,
  Modal,
  Form,
  Alert
} from 'antd';
import {
  LinkOutlined,
  DisconnectOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SendOutlined
} from '@ant-design/icons';
import axios from 'axios';

const { Title, Text, Paragraph } = Typography;

interface BindingStatus {
  is_bound: boolean;
  dingtalk_user_id?: string;
  dingtalk_name?: string;
  bound_at?: string;
}

const DingtalkBindingPanel: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [bindingStatus, setBindingStatus] = useState<BindingStatus | null>(null);
  const [bindModalVisible, setBindModalVisible] = useState(false);
  const [unbindModalVisible, setUnbindModalVisible] = useState(false);
  const [testMessageModalVisible, setTestMessageModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [testMessageForm] = Form.useForm();

  // 加载绑定状态
  const loadBindingStatus = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/v1/dingtalk/binding');
      setBindingStatus(response.data.data);
    } catch (error: any) {
      message.error('加载绑定状态失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  // 绑定钉钉账号
  const handleBind = async (values: any) => {
    try {
      setLoading(true);
      await axios.post('/api/v1/dingtalk/bind', {
        dingtalk_user_id: values.dingtalk_user_id,
        dingtalk_name: values.dingtalk_name
      });
      message.success('绑定成功！');
      setBindModalVisible(false);
      form.resetFields();
      await loadBindingStatus();
    } catch (error: any) {
      message.error('绑定失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  // 解除绑定
  const handleUnbind = async () => {
    try {
      setLoading(true);
      await axios.delete('/api/v1/dingtalk/unbind');
      message.success('解除绑定成功！');
      setUnbindModalVisible(false);
      await loadBindingStatus();
    } catch (error: any) {
      message.error('解除绑定失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  // 发送测试消息
  const handleSendTestMessage = async (values: any) => {
    try {
      setLoading(true);
      await axios.post('/api/v1/dingtalk/test-message', null, {
        params: { message: values.message }
      });
      message.success('测试消息发送成功！');
      setTestMessageModalVisible(false);
      testMessageForm.resetFields();
    } catch (error: any) {
      message.error('发送失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBindingStatus();
  }, []);

  return (
    <Card
      title={
        <Space>
          <LinkOutlined />
          <span>钉钉账号绑定</span>
        </Space>
      }
      loading={loading}
    >
      {/* 绑定状态显示 */}
      {bindingStatus && (
        <div>
          {bindingStatus.is_bound ? (
            <div>
              <Alert
                message="已绑定"
                description={
                  <div>
                    <p><strong>钉钉用户 ID:</strong> {bindingStatus.dingtalk_user_id}</p>
                    <p><strong>钉钉昵称:</strong> {bindingStatus.dingtalk_name}</p>
                    <p><strong>绑定时间:</strong> {new Date(bindingStatus.bound_at!).toLocaleString()}</p>
                  </div>
                }
                type="success"
                showIcon
                icon={<CheckCircleOutlined />}
              />
              
              <Divider />
              
              <Space>
                <Button
                  type="primary"
                  icon={<SendOutlined />}
                  onClick={() => setTestMessageModalVisible(true)}
                >
                  发送测试消息
                </Button>
                <Button
                  danger
                  icon={<DisconnectOutlined />}
                  onClick={() => setUnbindModalVisible(true)}
                >
                  解除绑定
                </Button>
              </Space>
            </div>
          ) : (
            <div>
              <Alert
                message="未绑定"
                description="您还没有绑定钉钉账号，绑定后可以通过钉钉发送消息来更新任务进度。"
                type="warning"
                showIcon
                icon={<CloseCircleOutlined />}
              />
              
              <Divider />
              
              <Title level={5}>如何绑定？</Title>
              <Paragraph>
                <ol>
                  <li>在钉钉中找到您的用户 ID（在钉钉设置中查看）</li>
                  <li>点击下方"绑定钉钉账号"按钮</li>
                  <li>输入您的钉钉用户 ID 和昵称</li>
                  <li>完成绑定后，您就可以通过钉钉发送消息来更新任务了</li>
                </ol>
              </Paragraph>
              
              <Button
                type="primary"
                icon={<LinkOutlined />}
                onClick={() => setBindModalVisible(true)}
              >
                绑定钉钉账号
              </Button>
            </div>
          )}
        </div>
      )}

      {/* 绑定对话框 */}
      <Modal
        title="绑定钉钉账号"
        open={bindModalVisible}
        onCancel={() => {
          setBindModalVisible(false);
          form.resetFields();
        }}
        footer={null}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleBind}
        >
          <Form.Item
            label="钉钉用户 ID"
            name="dingtalk_user_id"
            rules={[{ required: true, message: '请输入钉钉用户 ID' }]}
          >
            <Input placeholder="请输入您的钉钉用户 ID" />
          </Form.Item>
          
          <Form.Item
            label="钉钉昵称"
            name="dingtalk_name"
            rules={[{ required: true, message: '请输入钉钉昵称' }]}
          >
            <Input placeholder="请输入您的钉钉昵称" />
          </Form.Item>
          
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>
                确认绑定
              </Button>
              <Button onClick={() => {
                setBindModalVisible(false);
                form.resetFields();
              }}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 解除绑定确认对话框 */}
      <Modal
        title="解除绑定"
        open={unbindModalVisible}
        onOk={handleUnbind}
        onCancel={() => setUnbindModalVisible(false)}
        okText="确认解除"
        cancelText="取消"
        okButtonProps={{ danger: true, loading }}
      >
        <p>确定要解除钉钉账号绑定吗？</p>
        <p>解除后，您将无法通过钉钉发送消息来更新任务进度。</p>
      </Modal>

      {/* 测试消息对话框 */}
      <Modal
        title="发送测试消息"
        open={testMessageModalVisible}
        onCancel={() => {
          setTestMessageModalVisible(false);
          testMessageForm.resetFields();
        }}
        footer={null}
      >
        <Form
          form={testMessageForm}
          layout="vertical"
          onFinish={handleSendTestMessage}
        >
          <Form.Item
            label="测试消息内容"
            name="message"
            rules={[{ required: true, message: '请输入测试消息内容' }]}
            initialValue="这是一条测试消息"
          >
            <Input.TextArea
              rows={4}
              placeholder="请输入要发送的测试消息"
            />
          </Form.Item>
          
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>
                发送
              </Button>
              <Button onClick={() => {
                setTestMessageModalVisible(false);
                testMessageForm.resetFields();
              }}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

export default DingtalkBindingPanel;
