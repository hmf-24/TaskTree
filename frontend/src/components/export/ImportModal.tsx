import { useState } from 'react';
import { Modal, Upload, Button, message, Alert, Typography } from 'antd';
import { InboxOutlined, UploadOutlined } from '@ant-design/icons';
import { exportAPI } from '../../api';

const { Dragger } = Upload;
const { Text } = Typography;

interface ImportModalProps {
  projectId: number;
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function ImportModal({ projectId, open, onClose, onSuccess }: ImportModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<any>(null);

  const handleFileSelect = (info: any) => {
    const selectedFile = info.file.originFileObj || info.file;
    if (selectedFile.type !== 'application/json' && !selectedFile.name.endsWith('.json')) {
      message.error('请选择 JSON 格式的文件');
      return;
    }

    setFile(selectedFile);

    // 预览文件内容
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target?.result as string);
        setPreview(data);
      } catch {
        message.error('JSON 文件解析失败');
        setFile(null);
        setPreview(null);
      }
    };
    reader.readAsText(selectedFile);
  };

  const handleImport = async () => {
    if (!file) {
      message.warning('请先选择文件');
      return;
    }

    setLoading(true);
    try {
      const res = await exportAPI.importJson(projectId, file);
      if (res.code === 200 || res.code === 201) {
        message.success('导入成功');
        onSuccess();
        handleClose();
      } else {
        message.error(res.message || '导入失败');
      }
    } catch (error: any) {
      message.error(error.message || '导入失败');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setFile(null);
    setPreview(null);
    onClose();
  };

  return (
    <Modal
      title="导入任务数据"
      open={open}
      onCancel={handleClose}
      onOk={handleImport}
      okText="确认导入"
      okButtonProps={{ loading, disabled: !file }}
      width={500}
    >
      <Alert
        message="支持导入 TaskTree 导出的 JSON 格式文件"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Dragger
        accept=".json"
        maxCount={1}
        beforeUpload={() => false}
        onChange={handleFileSelect}
        showUploadList={false}
      >
        <p className="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p className="ant-upload-text">点击或拖拽 JSON 文件到此区域</p>
        <p className="ant-upload-hint">仅支持 .json 格式文件</p>
      </Dragger>

      {file && (
        <div style={{ marginTop: 16, padding: 12, background: '#fafafa', borderRadius: 6 }}>
          <Text strong>已选择文件：</Text>
          <Text>{file.name}</Text>
          <Text type="secondary" style={{ marginLeft: 8 }}>({(file.size / 1024).toFixed(1)} KB)</Text>
        </div>
      )}

      {preview && (
        <div style={{ marginTop: 12, padding: 12, background: '#fafafa', borderRadius: 6 }}>
          <Text strong>预览：</Text>
          <div style={{ marginTop: 8, fontSize: 13, color: '#666' }}>
            {preview.project_name && <div>项目名称: {preview.project_name}</div>}
            {preview.tasks && <div>任务数量: {Array.isArray(preview.tasks) ? preview.tasks.length : '未知'}</div>}
            {preview.tags && <div>标签数量: {Array.isArray(preview.tags) ? preview.tags.length : '未知'}</div>}
          </div>
        </div>
      )}
    </Modal>
  );
}
