import { useState, useEffect, useCallback } from 'react';
import { Card, Button, Space, Modal, Form, Input, DatePicker, message, Progress, Dropdown } from 'antd';
import { PlusOutlined, MoreOutlined, EditOutlined, DeleteOutlined, ArchiveOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
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
          message.error(error.message || '删除失败');
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
      key: 'edit',
      label: '编辑',
      icon: <EditOutlined />,
      onClick: () => navigate(`/project/${project.id}`),
    },
    {
      key: 'archive',
      label: '归档',
      icon: <ArchiveOutlined />,
      onClick: () => handleArchive(project.id),
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
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">我的项目</h1>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalVisible(true)}>
          新建项目
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {projects.map((project) => (
          <Card
            key={project.id}
            hoverable
            extra={
              <Dropdown menu={{ items: getMenuItems(project) }} trigger={['click']}>
                <Button type="text" icon={<MoreOutlined />} />
              </Dropdown>
            }
            onClick={() => navigate(`/project/${project.id}`)}
          >
            <Card.Meta
              title={<span className="text-lg font-medium">{project.name}</span>}
              description={
                <div className="mt-2">
                  <p className="text-gray-500 text-sm mb-2">{project.description || '暂无描述'}</p>
                  <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
                    <span>任务: {project.task_count || 0}</span>
                    <span>完成: {project.completed_count || 0}</span>
                  </div>
                  <Progress percent={progress(project)} size="small" />
                </div>
              }
            />
          </Card>
        ))}
      </div>

      {projects.length === 0 && !loading && (
        <div className="text-center text-gray-400 py-12">
          暂无项目，点击右上角创建第一个项目
        </div>
      )}

      <Modal
        title="新建项目"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={() => form.submit()}
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="name" label="项目名称" rules={[{ required: true, message: '请输入项目名称' }]}>
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