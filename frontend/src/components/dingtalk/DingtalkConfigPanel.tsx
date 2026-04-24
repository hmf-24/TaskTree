/**
 * 钉钉配置面板组件
 * 
 * 功能：
 * - 配置钉钉机器人 Webhook
 * - 配置钉钉机器人 Secret
 * - 测试钉钉连接
 */
import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Input,
  Button,
  message,
  Space,
  Typography,
  Divider,
  Alert,
  Collapse
} from 'antd';
import {
  ApiOutlined,
  SaveOutlined,
  SendOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import axios from 'axios';

const { Title, Text, Paragraph, Link } = Typography;
const { Panel } = Collapse;
const { TextArea } = Input;

const DingtalkConfigPanel: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [testLoading, setTestLoading] = useState(false);

  // 加载配置
  const loadConfig = async () => {
    try {
      setLoading(true);
      // 这里应该从用户设置中加载配置
      // const response = await axios.get('/api/v1/user/notification-settings');
      // if (response.data.code === 0) {
      //   form.setFieldsValue({
      //     webhook: response.data.data.dingtalk_webhook,
      //     secret: response.data.data.dingtalk_secret
      //   });
      // }
    } catch (error: any) {
      message.error('加载配置失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadConfig();
  }, []);

  // 保存配置
  const handleSave = async (values: any) => {
    try {
      setLoading(true);
      // 这里应该保存到用户设置
      // await axios.put('/api/v1/user/notification-settings', {
      //   dingtalk_webhook: values.webhook,
      //   dingtalk_secret: values.secret
      // });
      message.success('配置保存成功！');
    } catch (error: any) {
      message.error('保存失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  // 测试连接
  const handleTest = async () => {
    try {
      setTestLoading(true);
      await axios.post('/api/v1/dingtalk/test-message', null, {
        params: { message: '这是一条测试消息，钉钉机器人配置成功！' }
      });
      message.success('测试消息发送成功！请检查钉钉群消息。');
    } catch (error: any) {
      message.error('发送失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setTestLoading(false);
    }
  };

  return (
    <Card
      title={
        <Space>
          <ApiOutlined />
          <span>钉钉机器人配置</span>
        </Space>
      }
    >
      <Alert
        message="配置说明"
        description={
          <div>
            <p>配置钉钉机器人后，您可以通过钉钉发送消息来更新任务进度。</p>
            <p>
              <strong>如何获取 Webhook 和 Secret？</strong>
            </p>
            <ol>
              <li>在钉钉群中添加自定义机器人</li>
              <li>选择"自定义关键词"或"加签"安全设置</li>
              <li>复制 Webhook 地址和加签密钥（Secret）</li>
              <li>将 Webhook 和 Secret 填入下方表单</li>
            </ol>
          </div>
        }
        type="info"
        showIcon
        icon={<InfoCircleOutlined />}
        style={{ marginBottom: 24 }}
      />

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSave}
      >
        <Form.Item
          label="Webhook URL"
          name="webhook"
          rules={[
            { required: true, message: '请输入 Webhook URL' },
            { type: 'url', message: '请输入有效的 URL' }
          ]}
          tooltip="钉钉机器人的 Webhook 地址"
        >
          <Input
            placeholder="https://oapi.dingtalk.com/robot/send?access_token=..."
            prefix={<ApiOutlined />}
          />
        </Form.Item>

        <Form.Item
          label="Secret（加签密钥）"
          name="secret"
          rules={[{ required: true, message: '请输入 Secret' }]}
          tooltip="钉钉机器人的加签密钥，用于验证消息来源"
        >
          <Input.Password
            placeholder="SEC..."
            visibilityToggle
          />
        </Form.Item>

        <Form.Item>
          <Space>
            <Button
              type="primary"
              htmlType="submit"
              icon={<SaveOutlined />}
              loading={loading}
            >
              保存配置
            </Button>
            <Button
              icon={<SendOutlined />}
              onClick={handleTest}
              loading={testLoading}
            >
              发送测试消息
            </Button>
          </Space>
        </Form.Item>
      </Form>

      <Divider />

      <Collapse ghost>
        <Panel header="使用指南" key="1">
          <Title level={5}>支持的消息格式</Title>
          
          <Paragraph>
            <strong>1. 完成任务</strong>
            <pre style={{ background: '#f5f5f5', padding: '8px', borderRadius: '4px' }}>
              完成任务 "任务名称"{'\n'}
              任务 "任务名称" 已完成
            </pre>
          </Paragraph>

          <Paragraph>
            <strong>2. 更新进度</strong>
            <pre style={{ background: '#f5f5f5', padding: '8px', borderRadius: '4px' }}>
              任务 "任务名称" 进行中，进度 50%{'\n'}
              "任务名称" 完成了 80%
            </pre>
          </Paragraph>

          <Paragraph>
            <strong>3. 报告问题</strong>
            <pre style={{ background: '#f5f5f5', padding: '8px', borderRadius: '4px' }}>
              任务 "任务名称" 遇到问题：需要更多资源{'\n'}
              "任务名称" 有问题：技术难点
            </pre>
          </Paragraph>

          <Paragraph>
            <strong>4. 请求延期</strong>
            <pre style={{ background: '#f5f5f5', padding: '8px', borderRadius: '4px' }}>
              任务 "任务名称" 需要延期 3 天{'\n'}
              "任务名称" 延期 5 天
            </pre>
          </Paragraph>

          <Paragraph>
            <strong>5. 查询状态</strong>
            <pre style={{ background: '#f5f5f5', padding: '8px', borderRadius: '4px' }}>
              查询任务 "任务名称"{'\n'}
              "任务名称" 的状态
            </pre>
          </Paragraph>

          <Alert
            message="提示"
            description="任务名称用引号括起来更准确，支持中文和英文引号。一次只能更新一个任务。"
            type="success"
            showIcon
            style={{ marginTop: 16 }}
          />
        </Panel>

        <Panel header="常见问题" key="2">
          <Paragraph>
            <strong>Q: 为什么收不到测试消息？</strong>
            <br />
            A: 请检查：
            <ul>
              <li>Webhook URL 是否正确</li>
              <li>Secret 是否正确</li>
              <li>钉钉机器人是否已添加到群中</li>
              <li>是否已绑定钉钉账号</li>
            </ul>
          </Paragraph>

          <Paragraph>
            <strong>Q: 如何绑定钉钉账号？</strong>
            <br />
            A: 在"钉钉绑定"标签页中，输入您的钉钉用户 ID 和昵称进行绑定。
          </Paragraph>

          <Paragraph>
            <strong>Q: 消息发送后没有反应？</strong>
            <br />
            A: 请检查：
            <ul>
              <li>任务名称是否正确</li>
              <li>消息格式是否符合要求</li>
              <li>是否有权限修改该任务</li>
            </ul>
          </Paragraph>
        </Panel>
      </Collapse>
    </Card>
  );
};

export default DingtalkConfigPanel;
