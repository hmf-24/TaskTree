import { useState, useEffect, useCallback } from 'react';
import {
  Modal,
  Form,
  Input,
  Button,
  Tag,
  Space,
  ColorPicker,
  Popconfirm,
  message,
  Empty,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { tagsAPI } from '../../api';
import type { Tag as TagType } from '../../types';

interface TagManagerProps {
  projectId: number;
  open: boolean;
  onClose: () => void;
}

const DEFAULT_COLORS = [
  '#f5222d',
  '#fa541c',
  '#faad14',
  '#52c41a',
  '#1890ff',
  '#722ed1',
  '#eb2f96',
  '#13c2c2',
];

export default function TagManager({ projectId, open, onClose }: TagManagerProps) {
  const [tags, setTags] = useState<TagType[]>([]);
  const [loading, setLoading] = useState(false);
  const [editingTag, setEditingTag] = useState<TagType | null>(null);
  const [formVisible, setFormVisible] = useState(false);
  const [form] = Form.useForm();

  const fetchTags = useCallback(async () => {
    setLoading(true);
    try {
      const res = await tagsAPI.list(projectId);
      if (res.code === 200) {
        setTags(Array.isArray(res.data) ? res.data : []);
      }
    } catch (error: any) {
      message.error(error.message || '获取标签失败');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (open && projectId) {
      fetchTags();
    }
  }, [open, projectId, fetchTags]);

  const handleCreate = () => {
    setEditingTag(null);
    form.resetFields();
    form.setFieldValue('color', DEFAULT_COLORS[tags.length % DEFAULT_COLORS.length]);
    setFormVisible(true);
  };

  const handleEdit = (tag: TagType) => {
    setEditingTag(tag);
    form.setFieldsValue({ name: tag.name, color: tag.color });
    setFormVisible(true);
  };

  const handleDelete = async (tagId: number) => {
    try {
      const res = await tagsAPI.delete(tagId);
      if (res.code === 200) {
        message.success('删除成功');
        fetchTags();
      }
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      const color =
        typeof values.color === 'string'
          ? values.color
          : values.color?.toHexString?.() || values.color;
      if (editingTag) {
        const res = await tagsAPI.update(editingTag.id, { name: values.name, color });
        if (res.code === 200) {
          message.success('更新成功');
        }
      } else {
        const res = await tagsAPI.create(projectId, { name: values.name, color });
        if (res.code === 201) {
          message.success('创建成功');
        }
      }
      setFormVisible(false);
      form.resetFields();
      fetchTags();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  return (
    <Modal title="标签管理" open={open} onCancel={onClose} footer={null} width={480}>
      <div style={{ marginBottom: 16 }}>
        <Button type="dashed" icon={<PlusOutlined />} onClick={handleCreate} block>
          添加标签
        </Button>
      </div>

      {tags.length === 0 ? (
        <Empty description="暂无标签" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {tags.map((tag) => (
            <div
              key={tag.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '8px 12px',
                borderRadius: 6,
                background: '#fafafa',
              }}
            >
              <Tag color={tag.color} style={{ margin: 0, fontSize: 14 }}>
                {tag.name}
              </Tag>
              <Space size={4}>
                <Button
                  type="text"
                  size="small"
                  icon={<EditOutlined />}
                  onClick={() => handleEdit(tag)}
                />
                <Popconfirm
                  title="确定删除？"
                  onConfirm={() => handleDelete(tag.id)}
                  okText="删除"
                  cancelText="取消"
                >
                  <Button type="text" size="small" danger icon={<DeleteOutlined />} />
                </Popconfirm>
              </Space>
            </div>
          ))}
        </div>
      )}

      <Modal
        title={editingTag ? '编辑标签' : '添加标签'}
        open={formVisible}
        onCancel={() => setFormVisible(false)}
        onOk={() => form.submit()}
        width={360}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="name"
            label="标签名称"
            rules={[{ required: true, message: '请输入标签名称' }]}
          >
            <Input placeholder="输入标签名称" />
          </Form.Item>
          <Form.Item name="color" label="颜色">
            <ColorPicker presets={[{ label: '推荐', colors: DEFAULT_COLORS }]} showText />
          </Form.Item>
        </Form>
      </Modal>
    </Modal>
  );
}
