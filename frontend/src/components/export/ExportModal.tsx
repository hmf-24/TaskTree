import { useState } from 'react';
import { Modal, Button, Space, message, Radio } from 'antd';
import { DownloadOutlined, FileTextOutlined, FileExcelOutlined, FileMarkdownOutlined } from '@ant-design/icons';
import { exportAPI } from '../../api';

interface ExportModalProps {
  projectId: number;
  projectName: string;
  open: boolean;
  onClose: () => void;
}

type ExportFormat = 'json' | 'markdown' | 'excel';

export default function ExportModal({ projectId, projectName, open, onClose }: ExportModalProps) {
  const [format, setFormat] = useState<ExportFormat>('json');
  const [loading, setLoading] = useState(false);

  const formatOptions = [
    { label: <span><FileTextOutlined /> JSON</span>, value: 'json' },
    { label: <span><FileMarkdownOutlined /> Markdown</span>, value: 'markdown' },
    { label: <span><FileExcelOutlined /> Excel</span>, value: 'excel' },
  ];

  const handleExport = async () => {
    setLoading(true);
    try {
      let res: any;
      let filename: string;
      let mimeType: string;

      switch (format) {
        case 'json':
          res = await exportAPI.json(projectId);
          filename = `${projectName}.json`;
          mimeType = 'application/json';
          break;
        case 'markdown':
          res = await exportAPI.markdown(projectId);
          filename = `${projectName}.md`;
          mimeType = 'text/markdown';
          break;
        case 'excel':
          res = await exportAPI.excel(projectId);
          filename = `${projectName}.xlsx`;
          mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
          break;
      }

      // 创建下载 - axios 拦截器返回 response.data，对于 blob 请求它已经是 Blob 对象
      const blob = res instanceof Blob ? res : new Blob([res], { type: mimeType });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      message.success('导出成功');
      onClose();
    } catch (error: any) {
      message.error(error.message || '导出失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="导出项目数据"
      open={open}
      onCancel={onClose}
      footer={
        <Space>
          <Button onClick={onClose}>取消</Button>
          <Button type="primary" icon={<DownloadOutlined />} onClick={handleExport} loading={loading}>
            导出
          </Button>
        </Space>
      }
      width={400}
    >
      <div style={{ padding: '16px 0' }}>
        <p style={{ marginBottom: 16, color: '#666' }}>选择导出格式：</p>
        <Radio.Group
          value={format}
          onChange={(e) => setFormat(e.target.value)}
          optionType="button"
          buttonStyle="solid"
          options={formatOptions}
          size="large"
          style={{ width: '100%' }}
        />
        <div style={{ marginTop: 16, padding: 12, background: '#fafafa', borderRadius: 6, fontSize: 13, color: '#888' }}>
          {format === 'json' && '导出完整的项目数据，包括任务树、标签等，可用于备份或导入到其他项目。'}
          {format === 'markdown' && '导出为 Markdown 格式的任务清单，方便阅读和分享。'}
          {format === 'excel' && '导出为 Excel 表格，包含所有任务信息，适合数据分析和汇报。'}
        </div>
      </div>
    </Modal>
  );
}
