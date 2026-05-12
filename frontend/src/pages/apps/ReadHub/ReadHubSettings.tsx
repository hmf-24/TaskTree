import { useState, useEffect } from 'react';
import { Form, Input, InputNumber, Switch, Button, Card, Alert, message, Divider } from 'antd';
import { SaveOutlined, FolderOpenOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { Helmet } from 'react-helmet-async';
import { readhubSettingsAPI } from '../../../api/readhub';

export default function ReadHubSettings() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [obsidianConfigured, setObsidianConfigured] = useState(false);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const res: any = await readhubSettingsAPI.get();
        if (res.code === 200 && res.data) {
          form.setFieldsValue({
            obsidian_vault_path: res.data.obsidian_vault_path,
            obsidian_folder: res.data.obsidian_folder,
            auto_fetch_enabled: res.data.auto_fetch_enabled,
            auto_fetch_interval: res.data.auto_fetch_interval,
          });
          setObsidianConfigured(res.data.obsidian_configured);
        }
      } catch (e: any) {
        message.error(e.message || '加载设置失败');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [form]);

  const handleSave = async (values: any) => {
    setSaving(true);
    try {
      const res: any = await readhubSettingsAPI.update(values);
      if (res.code === 200) {
        message.success('设置已保存');
        setObsidianConfigured(res.data.obsidian_configured);
      } else {
        message.error(res.message || '保存失败');
      }
    } catch (e: any) {
      message.error(e.detail || e.message || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page-container" style={{ maxWidth: 680, margin: '0 auto', padding: '32px 24px' }}>
      <Helmet><title>ReadHub 设置 - Nexus</title></Helmet>

      <h2 style={{
        fontSize: 22, fontWeight: 600, marginBottom: 24,
        color: 'var(--color-ink)',
        fontFamily: 'var(--font-sans)',
      }}>
        ReadHub 设置
      </h2>

      <Card bordered={false} loading={loading} style={{
        background: 'var(--color-surface)',
        borderRadius: 'var(--radius-card)',
        border: '1px solid var(--color-border)',
      }}>
        <Form form={form} layout="vertical" onFinish={handleSave}>

          {/* ── Obsidian 集成 ── */}
          <Divider orientation="left">Obsidian 知识库集成</Divider>

          <Alert
            message="Obsidian 集成说明"
            description="配置后，您可以在阅读文章时一键将其保存为 Markdown 文件到您的 Obsidian Vault 中，并自动生成 YAML Frontmatter 元数据。"
            type="info"
            showIcon
            style={{ marginBottom: 20 }}
          />

          {obsidianConfigured ? (
            <Alert
              message="Obsidian 已连接"
              type="success"
              showIcon
              icon={<CheckCircleOutlined />}
              style={{ marginBottom: 16 }}
            />
          ) : (
            <Alert
              message="Obsidian 未配置"
              description="请填写 Vault 路径以启用 Obsidian 集成"
              type="warning"
              showIcon
              icon={<CloseCircleOutlined />}
              style={{ marginBottom: 16 }}
            />
          )}

          <Form.Item
            label="Obsidian Vault 路径"
            name="obsidian_vault_path"
            tooltip="您本机 Obsidian Vault 的绝对路径，例如 E:\Obsidian\MyVault"
          >
            <Input
              placeholder="例如：E:\Obsidian\MyVault"
              prefix={<FolderOpenOutlined />}
            />
          </Form.Item>

          <Form.Item
            label="保存子目录"
            name="obsidian_folder"
            tooltip="文章将保存到 Vault 下的此子目录中"
          >
            <Input placeholder="ReadHub" />
          </Form.Item>

          {/* ── 自动拉取 ── */}
          <Divider orientation="left">自动拉取</Divider>

          <Form.Item
            label="启用自动拉取"
            name="auto_fetch_enabled"
            valuePropName="checked"
            tooltip="开启后系统将定时自动拉取所有订阅源的最新文章"
          >
            <Switch checkedChildren="已启用" unCheckedChildren="已禁用" />
          </Form.Item>

          <Form.Item
            label="拉取间隔（分钟）"
            name="auto_fetch_interval"
            tooltip="两次自动拉取之间的最小间隔时间"
          >
            <InputNumber min={5} max={1440} style={{ width: 160 }} />
          </Form.Item>

          {/* ── 保存 ── */}
          <Form.Item style={{ marginTop: 24 }}>
            <Button
              type="primary"
              htmlType="submit"
              loading={saving}
              icon={<SaveOutlined />}
              block
            >
              保存设置
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
