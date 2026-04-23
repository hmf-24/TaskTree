import React, { useState, useEffect, useRef } from 'react';
import dayjs from 'dayjs';
import {
  Modal,
  Steps,
  Input,
  Button,
  List,
  Typography,
  Space,
  Table,
  Select,
  message,
  Popconfirm,
  Tag,
  Alert,
  DatePicker,
  InputNumber,
  Drawer,
} from 'antd';
import {
  RobotOutlined,
  UserOutlined,
  SendOutlined,
  PlusOutlined,
  DeleteOutlined,
  SaveOutlined,
  HistoryOutlined,
} from '@ant-design/icons';
import { llmTasksAPI, tasksAPI, conversationsAPI } from '../../api';
import type { Conversation } from '../../types';

const { TextArea } = Input;
const { Text } = Typography;

interface AITaskCreatorModalProps {
  projectId: number;
  parentId: number | null;
  open: boolean;
  onCancel: () => void;
  onSuccess: () => void;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface SubTask {
  id: string; // temp id for list
  name: string;
  description?: string;
  priority: string;
  estimated_hours?: number;
  start_date?: string;
  due_date?: string;
}

export default function AITaskCreatorModal({
  projectId,
  parentId,
  open,
  onCancel,
  onSuccess
}: AITaskCreatorModalProps) {
  const [currentStep, setCurrentStep] = useState(0);
  
  // Chat Step States
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [requirement, setRequirement] = useState('');
  
  // Decompose Step States
  const [subtasks, setSubtasks] = useState<SubTask[]>([]);
  const [decomposeLoading, setDecomposeLoading] = useState(false);
  const [saveLoading, setSaveLoading] = useState(false);
  
  // 对话历史状态
  const [historyOpen, setHistoryOpen] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  
  const chatListRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom
  useEffect(() => {
    if (chatListRef.current) {
      chatListRef.current.scrollTop = chatListRef.current.scrollHeight;
    }
  }, [chatMessages]);

  // Reset when opened
  useEffect(() => {
    if (open) {
      setCurrentStep(0);
      setChatMessages([]);
      setInputValue('');
      setRequirement('');
      setSubtasks([]);
    }
  }, [open]);

  // 加载对话历史
  const fetchConversations = async () => {
    setLoadingHistory(true);
    try {
      const res = await conversationsAPI.list({
        project_id: projectId,
        conversation_type: 'create',
      });
      if (res.code === 200) {
        setConversations(res.data || []);
      }
    } catch (error: any) {
      message.error('加载对话历史失败');
    } finally {
      setLoadingHistory(false);
    }
  };

  // 加载历史对话
  const loadConversation = async (conv: Conversation) => {
    try {
      // 将历史消息转换为当前格式
      const messages = conv.messages.map((msg) => ({
        role: msg.role,
        content: msg.content,
      }));
      setChatMessages(messages);
      setRequirement(messages.map((m) => `${m.role}: ${m.content}`).join('\n'));
      setHistoryOpen(false);
      message.success('已加载历史对话');
    } catch (error: any) {
      message.error('加载对话失败');
    }
  };

  const handleSendChat = async () => {
    if (!inputValue.trim()) return;
    
    const newMessages = [...chatMessages, { role: 'user' as const, content: inputValue.trim() }];
    setChatMessages(newMessages);
    setInputValue('');
    setChatLoading(true);
    
    try {
      // 保持最近 15 轮对话 (30条消息)
      const recentMessages = newMessages.slice(-30);
      const res = await llmTasksAPI.clarify({
        project_id: projectId,
        messages: recentMessages
      });
      
      if (res.code === 200 && res.data?.reply) {
        setChatMessages([...newMessages, { role: 'assistant', content: res.data.reply }]);
        setRequirement(newMessages.map(m => `${m.role}: ${m.content}`).join('\n') + `\nassistant: ${res.data.reply}`);
      } else {
        throw new Error(res.message || 'LLM 对话失败');
      }
    } catch (err: any) {
      console.error('LLM clarify error:', err);
      let errorMsg = 'LLM 对话失败';
      
      if (err.response?.status === 400) {
        errorMsg = err.response.data?.detail || '未配置大模型服务，请先在【设置 → 智能提醒】中配置';
      } else if (err.response?.status === 504) {
        errorMsg = 'LLM 服务响应超时，请稍后重试';
      } else if (err.response?.status === 429) {
        errorMsg = 'API 调用频率超限，请稍后重试';
      } else if (err.message) {
        errorMsg = err.message;
      }
      
      message.error(errorMsg, 5);
      // 移除刚才用户发送的消息，方便重试
      setChatMessages(newMessages.slice(0, -1));
      setInputValue(inputValue);
    } finally {
      setChatLoading(false);
    }
  };

  const handleDecompose = async () => {
    if (chatMessages.length === 0) {
      message.warning('请先描述您的任务需求');
      return;
    }
    
    setDecomposeLoading(true);
    setCurrentStep(1); // 切换到第二步，显示加载状态
    
    try {
      const finalReq = requirement || chatMessages.map(m => m.content).join('\n');
      const res = await llmTasksAPI.decompose({
        project_id: projectId,
        requirement: finalReq
      });
      
      if (res.code === 200 && res.data?.subtasks) {
        const tasks = res.data.subtasks.map((t: any, index: number) => ({
          id: `temp-${Date.now()}-${index}`,
          name: t.name || '未命名子任务',
          description: t.description || '',
          priority: ['low', 'medium', 'high', 'urgent'].includes(t.priority) ? t.priority : 'medium',
          estimated_hours: t.estimated_hours,
          start_date: t.start_date,
          due_date: t.due_date
        }));
        
        if (tasks.length === 0) {
          message.warning('AI 未能生成子任务，请尝试更详细地描述需求');
          setCurrentStep(0);
        } else {
          setSubtasks(tasks);
          message.success(`成功生成 ${tasks.length} 个子任务`);
        }
      } else {
        throw new Error(res.message || '任务分解失败');
      }
    } catch (err: any) {
      console.error('LLM decompose error:', err);
      let errorMsg = '任务分解失败';
      
      if (err.response?.status === 400) {
        errorMsg = err.response.data?.detail || '未配置大模型服务，请先在【设置 → 智能提醒】中配置';
      } else if (err.response?.status === 504) {
        errorMsg = 'LLM 服务响应超时，请稍后重试';
      } else if (err.response?.status === 429) {
        errorMsg = 'API 调用频率超限，请稍后重试';
      } else if (err.response?.status === 500 && err.response.data?.detail) {
        errorMsg = err.response.data.detail;
      } else if (err.message) {
        errorMsg = err.message;
      }
      
      message.error(errorMsg, 5);
      setCurrentStep(0); // 失败回到第一步
    } finally {
      setDecomposeLoading(false);
    }
  };

  const handleAddSubtask = () => {
    setSubtasks([
      ...subtasks, 
      { id: `temp-${Date.now()}`, name: '新子任务', description: '', priority: 'medium' }
    ]);
  };

  const handleUpdateSubtask = (id: string, field: string, value: string) => {
    setSubtasks(subtasks.map(t => t.id === id ? { ...t, [field]: value } : t));
  };

  const handleDeleteSubtask = (id: string) => {
    setSubtasks(subtasks.filter(t => t.id !== id));
  };

  const handleSave = async () => {
    if (!requirement && chatMessages.length === 0) {
      message.warning('任务需求为空');
      return;
    }
    
    // 生成父任务名称 (取用户第一句话的前20个字符)
    const firstUserMsg = chatMessages.find(m => m.role === 'user')?.content || '智能创建任务';
    const parentName = firstUserMsg.length > 20 ? firstUserMsg.substring(0, 20) + '...' : firstUserMsg;
    
    setSaveLoading(true);
    try {
      await tasksAPI.createWithSubtasks(projectId, {
        name: parentName,
        description: requirement || firstUserMsg,
        priority: 'medium',
        parent_id: parentId,
        subtasks: subtasks.map(t => ({
          name: t.name,
          description: t.description,
          priority: t.priority,
          estimated_time: t.estimated_hours,
          start_date: t.start_date,
          due_date: t.due_date
        }))
      });
      
      message.success('智能任务创建成功！');
      onSuccess();
    } catch (err: any) {
      message.error(err.message || '保存任务失败');
    } finally {
      setSaveLoading(false);
    }
  };

  const columns = [
    {
      title: '子任务名称',
      dataIndex: 'name',
      key: 'name',
      width: '20%',
      render: (text: string, record: SubTask) => (
        <Input 
          value={text} 
          onChange={e => handleUpdateSubtask(record.id, 'name', e.target.value)} 
          placeholder="子任务名称"
        />
      )
    },
    {
      title: '描述说明',
      dataIndex: 'description',
      key: 'description',
      width: '25%',
      render: (text: string, record: SubTask) => (
        <TextArea 
          value={text} 
          onChange={e => handleUpdateSubtask(record.id, 'description', e.target.value)} 
          autoSize={{ minRows: 1, maxRows: 2 }}
          placeholder="详细说明"
        />
      )
    },
    {
      title: '工时(h)',
      dataIndex: 'estimated_hours',
      key: 'estimated_hours',
      width: '10%',
      render: (value: number, record: SubTask) => (
        <InputNumber 
          value={value} 
          onChange={val => handleUpdateSubtask(record.id, 'estimated_hours', val?.toString() || '')} 
          placeholder="工时"
          min={0}
          style={{ width: '100%' }}
        />
      )
    },
    {
      title: '开始日期',
      dataIndex: 'start_date',
      key: 'start_date',
      width: '13%',
      render: (value: string, record: SubTask) => (
        <DatePicker 
          value={value ? dayjs(value) : null} 
          onChange={(date) => handleUpdateSubtask(record.id, 'start_date', date?.format('YYYY-MM-DD') || '')} 
          placeholder="开始日期"
          style={{ width: '100%' }}
          format="YYYY-MM-DD"
        />
      )
    },
    {
      title: '截止日期',
      dataIndex: 'due_date',
      key: 'due_date',
      width: '13%',
      render: (value: string, record: SubTask) => (
        <DatePicker 
          value={value ? dayjs(value) : null} 
          onChange={(date) => handleUpdateSubtask(record.id, 'due_date', date?.format('YYYY-MM-DD') || '')} 
          placeholder="截止日期"
          style={{ width: '100%' }}
          format="YYYY-MM-DD"
        />
      )
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: '10%',
      render: (text: string, record: SubTask) => (
        <Select 
          value={text} 
          onChange={value => handleUpdateSubtask(record.id, 'priority', value)}
          style={{ width: '100%' }}
        >
          <Select.Option value="low">低</Select.Option>
          <Select.Option value="medium">中</Select.Option>
          <Select.Option value="high">高</Select.Option>
          <Select.Option value="urgent">紧急</Select.Option>
        </Select>
      )
    },
    {
      title: '操作',
      key: 'action',
      width: '9%',
      render: (_: any, record: SubTask) => (
        <Popconfirm title="确定删除该子任务？" onConfirm={() => handleDeleteSubtask(record.id)}>
          <Button type="text" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      )
    }
  ];

  return (
    <>
      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span>✨ AI 智能任务创建</span>
            <Button
              type="text"
              icon={<HistoryOutlined />}
              onClick={() => {
                fetchConversations();
                setHistoryOpen(true);
              }}
            >
              历史对话
            </Button>
          </div>
        }
        open={open}
        onCancel={onCancel}
        width={1200}
        footer={null}
        destroyOnClose
      >
      <Steps 
        current={currentStep} 
        items={[
          { title: '需求澄清', description: '与AI对话细化需求' },
          { title: '结构分解', description: '确认并编辑子任务' }
        ]} 
        style={{ marginBottom: 24 }}
      />
      
      {currentStep === 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', height: '400px' }}>
          <Alert 
            message="提示: 在这里输入您想创建的任务,例如「做一个用户登录页面」,AI会帮您追问细节直到需求清晰为止。" 
            type="info" 
            showIcon 
            style={{ marginBottom: 16 }}
          />
          
          <div 
            ref={chatListRef}
            style={{ 
              flex: 1, 
              overflowY: 'auto', 
              padding: '16px', 
              background: '#f5f5f5', 
              borderRadius: '8px',
              marginBottom: '16px'
            }}
          >
            {chatMessages.length === 0 ? (
              <div style={{ textAlign: 'center', color: '#999', marginTop: '100px' }}>
                <RobotOutlined style={{ fontSize: '32px', marginBottom: '8px' }} />
                <div>嗨！我是您的 AI 助理。请告诉我您想创建什么任务？</div>
              </div>
            ) : (
              <List
                dataSource={chatMessages}
                renderItem={item => (
                  <List.Item style={{ borderBottom: 'none', padding: '8px 0' }}>
                    <div style={{ 
                      display: 'flex', 
                      width: '100%',
                      justifyContent: item.role === 'user' ? 'flex-end' : 'flex-start'
                    }}>
                      <div style={{ 
                        maxWidth: '80%', 
                        display: 'flex', 
                        gap: '8px',
                        flexDirection: item.role === 'user' ? 'row-reverse' : 'row'
                      }}>
                        <div style={{ marginTop: '4px' }}>
                          {item.role === 'user' ? <UserOutlined style={{ fontSize: 20 }} /> : <RobotOutlined style={{ fontSize: 20, color: '#1890ff' }} />}
                        </div>
                        <div style={{ 
                          padding: '10px 14px', 
                          borderRadius: '8px',
                          background: item.role === 'user' ? '#1890ff' : '#fff',
                          color: item.role === 'user' ? '#fff' : '#333',
                          boxShadow: '0 1px 2px rgba(0,0,0,0.1)',
                          whiteSpace: 'pre-wrap'
                        }}>
                          {item.content}
                        </div>
                      </div>
                    </div>
                  </List.Item>
                )}
              />
            )}
            {chatLoading && (
              <div style={{ display: 'flex', gap: '8px', marginTop: '16px' }}>
                <RobotOutlined style={{ fontSize: 20, color: '#1890ff', marginTop: '4px' }} />
                <div style={{ padding: '10px 14px', background: '#fff', borderRadius: '8px', color: '#999' }}>
                  AI 正在思考...
                </div>
              </div>
            )}
          </div>
          
          <div style={{ display: 'flex', gap: '8px' }}>
            <TextArea 
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              placeholder="描述您的需求细节..."
              autoSize={{ minRows: 2, maxRows: 4 }}
              onPressEnter={(e) => {
                if (!e.shiftKey) {
                  e.preventDefault();
                  handleSendChat();
                }
              }}
              disabled={chatLoading}
            />
            <Button 
              type="primary" 
              icon={<SendOutlined />} 
              onClick={handleSendChat} 
              loading={chatLoading}
              style={{ height: 'auto' }}
            >
              发送
            </Button>
          </div>
          
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '16px' }}>
            <Button 
              type="primary" 
              onClick={handleDecompose}
              disabled={chatMessages.length === 0 || chatLoading}
            >
              需求已清晰，进行任务分解
            </Button>
          </div>
        </div>
      )}

      {currentStep === 1 && (
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <Alert 
            message="AI 已经为您将任务拆解成以下步骤,您可以直接在表格中修改、增加或删除子任务。" 
            type="success" 
            showIcon 
            style={{ marginBottom: 16 }}
          />
          
          <Table 
            dataSource={subtasks} 
            columns={columns} 
            rowKey="id" 
            pagination={false}
            loading={decomposeLoading}
            size="small"
            style={{ marginBottom: '16px' }}
          />
          
          <Button 
            type="dashed" 
            onClick={handleAddSubtask} 
            block 
            icon={<PlusOutlined />}
            style={{ marginBottom: '24px' }}
          >
            添加新子任务
          </Button>
          
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <Button onClick={() => setCurrentStep(0)}>返回补充需求</Button>
            <Button 
              type="primary" 
              icon={<SaveOutlined />} 
              onClick={handleSave}
              loading={saveLoading}
            >
              确认生成任务树
            </Button>
          </div>
        </div>
      )}
    </Modal>

    {/* 历史对话抽屉 */}
    <Drawer
      title="历史对话"
      open={historyOpen}
      onClose={() => setHistoryOpen(false)}
      width={400}
    >
      <List
        loading={loadingHistory}
        dataSource={conversations}
        renderItem={(conv) => (
          <List.Item
            onClick={() => loadConversation(conv)}
            style={{ cursor: 'pointer' }}
          >
            <List.Item.Meta
              title={conv.title || '任务创建对话'}
              description={
                <>
                  <Tag color="purple">任务创建</Tag>
                  <span>{dayjs(conv.created_at).format('YYYY-MM-DD HH:mm')}</span>
                </>
              }
            />
          </List.Item>
        )}
      />
    </Drawer>
  </>
  );
}
