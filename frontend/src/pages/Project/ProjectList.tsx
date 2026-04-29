import { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Button,
  Space,
  Modal,
  Form,
  Input,
  DatePicker,
  message,
  Progress,
  Dropdown,
  Spin,
  Empty,
} from 'antd';
import {
  PlusOutlined,
  MoreOutlined,
  DeleteOutlined,
  FolderOpenOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { projectsAPI } from '../../api';
import { PROJECT_STATUS } from '../../constants';

export default function ProjectList() {
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [form] = Form.useForm();
  const navigate = useNavigate();

  const fetchProjects = useCallback(async () => {
    setLoading(true);
    try {
      const res = await projectsAPI.list({ status: PROJECT_STATUS.ACTIVE });
      if (res.code === 200) {
        setProjects(res.data.items || []);
      }
    } catch (error: any) {
      message.error(error.message || '获取项目列表失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const handleCreate = async (values: any) => {
    try {
      const data = {
        name: values.name,
        description: values.description,
        start_date: values.dateRange?.[0]?.format('YYYY-MM-DD'),
        end_date: values.dateRange?.[1]?.format('YYYY-MM-DD'),
      };
      const res = await projectsAPI.create(data);
      if (res.code === 201) {
        message.success('创建成功');
        setModalVisible(false);
        form.resetFields();
        fetchProjects();
      } else {
        message.error(res.message || '创建失败');
      }
    } catch (error: any) {
      message.error(error.message || '创建失败');
    }
  };

  const handleDelete = async (id: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '删除后无法恢复，确定要删除该项目吗？',
      okText: '确认',
      cancelText: '取消',
      okType: 'danger',
      onOk: async () => {
        try {
          const res = await projectsAPI.delete(id);
          if (res.code === 200) {
            message.success('删除成功');
            fetchProjects();
          } else {
            message.error(res.message || '删除失败');
          }
        } catch (error: any) {
          // 处理特殊错误场景
          if (error.message?.includes('timeout')) {
            message.error('请求超时，请稍后重试');
          } else if (error.message?.includes('Network') || error.message?.includes('network')) {
            message.error('网络连接失败，请检查网络');
          } else {
            message.error(error.message || '删除失败');
          }
        }
      },
    });
  };

  const handleArchive = async (id: number) => {
    try {
      const res = await projectsAPI.archive(id, true);
      if (res.code === 200) {
        message.success('归档成功');
        fetchProjects();
      } else {
        message.error(res.message || '归档失败');
      }
    } catch (error: any) {
      message.error(error.message || '归档失败');
    }
  };

  const getMenuItems = (project: any) => [
    {
      key: 'enter',
      label: '进入项目',
      icon: <FolderOpenOutlined />,
      onClick: () => navigate(`/project/${project.id}`),
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'delete',
      label: '删除',
      icon: <DeleteOutlined />,
      danger: true,
      onClick: () => handleDelete(project.id),
    },
  ];

  const progress = (project: any) => {
    if (!project.task_count) return 0;
    return Math.round((project.completed_count / project.task_count) * 100);
  };

  return (
    <div className="page-container">
      <Helmet><title>项目列表 - TaskTree</title></Helmet>
      <div className="flex justify-between items-center mb-6">
        <h1 className="page-title" style={{ margin: 0 }}>我的项目</h1>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalVisible(true)}>
          新建项目
        </Button>
      </div>

      <Spin spinning={loading}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 24 }}>
          {/* 新建项目卡片占位 */}
          <div
            className="stagger-item glass-panel"
            style={{
              border: '2px dashed var(--color-border)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              padding: 24,
              minHeight: 180,
              cursor: 'pointer',
              transition: 'all var(--duration-fast) var(--ease-smooth)',
              animationDelay: '0ms',
            }}
            onClick={() => setModalVisible(true)}
            onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.borderColor = 'var(--color-border-strong)'; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.borderColor = 'var(--color-border)'; }}
          >
            <PlusOutlined style={{ fontSize: 32, color: 'var(--color-ink-tertiary)', marginBottom: 12 }} />
            <span style={{ color: 'var(--color-ink-secondary)', fontWeight: 500 }}>创建新项目</span>
          </div>

          {projects.map((project, index) => (
            <div
              key={project.id}
              className="stagger-item glass-panel"
              style={{
                padding: 20,
                cursor: 'pointer',
                transition: 'all var(--duration-normal) var(--ease-smooth)',
                animationDelay: `${(index + 1) * 50}ms`,
                position: 'relative',
                display: 'flex',
                flexDirection: 'column',
                minHeight: 180,
              }}
              onClick={() => navigate(`/project/${project.id}`)}
              onMouseEnter={(e) => {
                const target = e.currentTarget as HTMLElement;
                target.style.transform = 'translateY(-2px)';
                target.style.boxShadow = 'var(--shadow-card)';
                target.style.borderColor = 'var(--color-border-strong)';
              }}
              onMouseLeave={(e) => {
                const target = e.currentTarget as HTMLElement;
                target.style.transform = 'translateY(0)';
                target.style.boxShadow = 'none';
                target.style.borderColor = 'var(--color-border)';
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: 'var(--color-ink)', letterSpacing: '-0.01em', lineHeight: 1.4 }}>
                  {project.name}
                </h3>
                <Dropdown
                  menu={{ items: getMenuItems(project) }}
                  trigger={['click']}
                >
                  <Button
                    type="text"
                    icon={<MoreOutlined />}
                    onClick={(e) => e.stopPropagation()}
                    style={{ color: 'var(--color-ink-tertiary)', padding: '0 4px', height: 24, marginTop: -4, marginRight: -8 }}
                  />
                </Dropdown>
              </div>

              {project.description && (
                <p style={{
                  color: 'var(--color-ink-secondary)',
                  fontSize: 13,
                  lineHeight: 1.5,
                  marginBottom: 16,
                  display: '-webkit-box',
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical',
                  overflow: 'hidden'
                }}>
                  {project.description}
                </p>
              )}

              <div style={{
                display: 'flex',
                gap: 16,
                fontSize: 12,
                color: 'var(--color-ink-tertiary)',
                marginTop: 'auto',
                paddingTop: 16,
                borderTop: '1px solid var(--color-border)'
              }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--color-brand)' }} />
                  <span style={{ fontVariantNumeric: 'tabular-nums', fontWeight: 500, color: 'var(--color-ink)' }}>{project.task_count || 0}</span> 任务
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#346538' }} />
                  <span style={{ fontVariantNumeric: 'tabular-nums', fontWeight: 500, color: 'var(--color-ink)' }}>{project.completed_count || 0}</span> 已完成
                </span>
              </div>
            </div>
          ))}
        </div>
      </Spin>

      {projects.length === 0 && !loading && (
        <Empty
          description="还没有任何项目"
          style={{ padding: 64 }}
        >
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalVisible(true)}>
            创建第一个项目
          </Button>
        </Empty>
      )}

      <Modal
        title="新建项目"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={() => form.submit()}
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item
            name="name"
            label="项目名称"
            rules={[{ required: true, message: '请输入项目名称' }]}
          >
            <Input placeholder="请输入项目名称" />
          </Form.Item>
          <Form.Item name="description" label="项目描述">
            <Input.TextArea rows={3} placeholder="请输入项目描述" />
          </Form.Item>
          <Form.Item name="dateRange" label="时间范围">
            <DatePicker.RangePicker style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
