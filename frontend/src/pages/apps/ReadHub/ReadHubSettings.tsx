import { useState, useEffect } from 'react';
import { Form, Input, InputNumber, Switch, Button, Card, Alert, message, Divider, Space, Tag, Select } from 'antd';
import {
  SaveOutlined, FolderOpenOutlined, CheckCircleOutlined, CloseCircleOutlined,
  LinkOutlined, SyncOutlined, WechatOutlined, ApiOutlined,
} from '@ant-design/icons';
import { Helmet } from 'react-helmet-async';
import { readhubSettingsAPI, wewerssAPI } from '../../../api/readhub';

export default function ReadHubSettings() {
  const [form] = Form.useForm();
  const streamEnabled = Form.useWatch('dingtalk_stream_enabled', form);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [obsidianConfigured, setObsidianConfigured] = useState(false);

  // wewe-rss 状态
  const [weweUrl, setWeweUrl] = useState('');
  const [weweAuthCode, setWeweAuthCode] = useState('');
  const [weweConnected, setWeweConnected] = useState<boolean | null>(null);
  const [weweFeedCount, setWeweFeedCount] = useState(0);
  const [weweChecking, setWeweChecking] = useState(false);
  const [weweSyncing, setWeweSyncing] = useState(false);
  const [weweSyncResult, setWeweSyncResult] = useState<{ added: string[]; skipped: string[] } | null>(null);

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
            auto_fetch_interval_value: res.data.auto_fetch_interval >= 1440 && res.data.auto_fetch_interval % 1440 === 0 ? res.data.auto_fetch_interval / 1440 : (res.data.auto_fetch_interval >= 60 && res.data.auto_fetch_interval % 60 === 0 ? res.data.auto_fetch_interval / 60 : res.data.auto_fetch_interval || 60),
            auto_fetch_interval_unit: res.data.auto_fetch_interval >= 1440 && res.data.auto_fetch_interval % 1440 === 0 ? 'days' : (res.data.auto_fetch_interval >= 60 && res.data.auto_fetch_interval % 60 === 0 ? 'hours' : 'minutes'),
            dingtalk_stream_enabled: res.data.dingtalk_stream_enabled,
            dingtalk_client_id: res.data.dingtalk_client_id,
            dingtalk_client_secret: res.data.dingtalk_client_secret,
            dingtalk_webhook: res.data.dingtalk_webhook,
            dingtalk_secret: res.data.dingtalk_secret,
            wewe_server_url: res.data.wewe_server_url,
            wewe_auth_code: res.data.wewe_auth_code,
            interest_tags: res.data.interest_tags ? (typeof res.data.interest_tags === 'string' ? JSON.parse(res.data.interest_tags) : res.data.interest_tags) : ["AI", "前沿技术", "数据中心", "算力", "GPU"],
          });
          if (res.data.wewe_server_url) setWeweUrl(res.data.wewe_server_url);
          if (res.data.wewe_auth_code) setWeweAuthCode(res.data.wewe_auth_code);
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
    // 附带独立的 wewe 状态
    values.wewe_server_url = weweUrl.trim();
    values.wewe_auth_code = weweAuthCode.trim();
    
    // 格式化 interest_tags
    if (values.interest_tags && Array.isArray(values.interest_tags)) {
      values.interest_tags = JSON.stringify(values.interest_tags);
    }
    
    // 换算拉取间隔
    const multiplier = values.auto_fetch_interval_unit === 'days' ? 1440 : (values.auto_fetch_interval_unit === 'hours' ? 60 : 1);
    values.auto_fetch_interval = (values.auto_fetch_interval_value || 60) * multiplier;
    delete values.auto_fetch_interval_value;
    delete values.auto_fetch_interval_unit;
    
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

  // wewe-rss 连接测试
  const handleWeweCheck = async () => {
    if (!weweUrl.trim()) {
      message.warning('请先输入 wewe-rss 服务地址');
      return;
    }
    setWeweChecking(true);
    setWeweConnected(null);
    try {
      const res: any = await wewerssAPI.checkStatus(weweUrl.trim(), weweAuthCode || undefined);
      if (res.code === 200 && res.data) {
        setWeweConnected(res.data.connected);
        setWeweFeedCount(res.data.feed_count || 0);
        if (res.data.connected) {
          message.success(`已连接！检测到 ${res.data.feed_count || 0} 个订阅源`);
        } else {
          message.error(`连接失败: ${res.data.error || '未知错误'}`);
        }
      }
    } catch (e: any) {
      setWeweConnected(false);
      message.error(e.detail || e.message || '连接测试失败');
    } finally {
      setWeweChecking(false);
    }
  };

  // wewe-rss 同步
  const handleWeweSync = async () => {
    if (!weweUrl.trim()) {
      message.warning('请先输入 wewe-rss 服务地址');
      return;
    }
    setWeweSyncing(true);
    setWeweSyncResult(null);
    try {
      const res: any = await wewerssAPI.sync({
        server_url: weweUrl.trim(),
        auth_code: weweAuthCode || undefined,
      });
      if (res.code === 200) {
        message.success(res.message);
        setWeweSyncResult(res.data);
      } else {
        message.error(res.message || '同步失败');
      }
    } catch (e: any) {
      message.error(e.detail || e.message || '同步失败');
    } finally {
      setWeweSyncing(false);
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

      {/* ══════════ wewe-rss 集成卡片 ══════════ */}
      <Card
        bordered={false}
        className="glass-card"
        style={{ marginBottom: 24, padding: 0 }}
        styles={{ body: { padding: 24 } }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: 'linear-gradient(135deg, #07C160, #1AAD19)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <WechatOutlined style={{ color: '#fff', fontSize: 18 }} />
          </div>
          <div>
            <div style={{ fontWeight: 600, fontSize: 15, color: 'var(--color-ink)' }}>
              WeWe-RSS 集成
            </div>
            <div style={{ fontSize: 12, color: 'var(--color-ink-tertiary)' }}>
              自动同步微信公众号订阅源
            </div>
          </div>
          {weweConnected === true && (
            <Tag color="success" style={{ marginLeft: 'auto' }}>
              <CheckCircleOutlined /> 已连接 · {weweFeedCount} 个源
            </Tag>
          )}
          {weweConnected === false && (
            <Tag color="error" style={{ marginLeft: 'auto' }}>
              <CloseCircleOutlined /> 未连接
            </Tag>
          )}
        </div>

        <Alert
          message="部署 wewe-rss 后，在此输入服务地址即可一键导入所有微信公众号到 ReadHub"
          type="info"
          showIcon
          icon={<ApiOutlined />}
          style={{ marginBottom: 16, fontSize: 13 }}
        />

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div>
            <label style={{ fontSize: 12, fontWeight: 500, color: 'var(--color-ink-secondary)', marginBottom: 4, display: 'block' }}>
              服务地址
            </label>
            <Input
              placeholder="例如：http://localhost:4000"
              prefix={<LinkOutlined style={{ color: 'var(--color-ink-tertiary)' }} />}
              value={weweUrl}
              onChange={(e) => setWeweUrl(e.target.value)}
            />
          </div>
          <div>
            <label style={{ fontSize: 12, fontWeight: 500, color: 'var(--color-ink-secondary)', marginBottom: 4, display: 'block' }}>
              授权码 <span style={{ color: 'var(--color-ink-tertiary)', fontWeight: 400 }}>(可选，仅在 wewe-rss 设置了 AUTH_CODE 时需要)</span>
            </label>
            <Input.Password
              placeholder="留空表示无需授权"
              value={weweAuthCode}
              onChange={(e) => setWeweAuthCode(e.target.value)}
            />
          </div>
          <Space style={{ marginTop: 4 }}>
            <Button
              onClick={handleWeweCheck}
              loading={weweChecking}
              icon={<ApiOutlined />}
            >
              测试连接
            </Button>
            <Button
              type="primary"
              onClick={handleWeweSync}
              loading={weweSyncing}
              disabled={weweConnected !== true}
              icon={<SyncOutlined />}
            >
              一键同步
            </Button>
          </Space>
        </div>

        {/* 同步结果 */}
        {weweSyncResult && (
          <div style={{ marginTop: 16, padding: 12, background: 'rgba(0,0,0,0.02)', borderRadius: 'var(--radius-button)' }}>
            {weweSyncResult.added.length > 0 && (
              <div style={{ marginBottom: 8 }}>
                <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--color-ink-secondary)' }}>
                  ✅ 新增 {weweSyncResult.added.length} 个源：
                </span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 4 }}>
                  {weweSyncResult.added.map((name, i) => (
                    <Tag key={i} color="green" style={{ fontSize: 11 }}>{name}</Tag>
                  ))}
                </div>
              </div>
            )}
            {weweSyncResult.skipped.length > 0 && (
              <div>
                <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--color-ink-tertiary)' }}>
                  已存在 {weweSyncResult.skipped.length} 个（已跳过）
                </span>
              </div>
            )}
          </div>
        )}
      </Card>

      {/* ══════════ 原有设置卡片 ══════════ */}
      <Card bordered={false} loading={loading} className="glass-card" styles={{ body: { padding: 24 } }}>
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

          {/* ── 智能过滤与分级 ── */}
          <Divider orientation="left">智能过滤与分级</Divider>
          
          <Alert
            message="智能标签过滤说明"
            description="当自动拉取文章时，大模型会根据您的关注标签为每篇文章评分（高优、普通、低优、无关）。高优文章会在日报中作为今日概览；无关内容将被折叠隐藏，不予推送。"
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />

          <Form.Item
            label="关注标签"
            name="interest_tags"
            tooltip="输入标签并回车添加。大模型会根据这些标签评估文章的相关度。"
          >
            <Select
              mode="tags"
              placeholder="输入自定义标签后，按回车键添加"
              style={{ width: '100%' }}
              options={[
                { value: 'AI', label: 'AI' },
                { value: '大模型', label: '大模型' },
                { value: '前沿技术', label: '前沿技术' },
                { value: '数据中心', label: '数据中心' },
                { value: '算力', label: '算力' },
                { value: 'GPU', label: 'GPU' },
              ]}
            />
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

          <Form.Item label="拉取间隔" tooltip="两次自动拉取之间的最小间隔时间">
            <Space.Compact>
              <Form.Item name="auto_fetch_interval_value" noStyle rules={[{ required: true, message: '请输入数值' }]}>
                <InputNumber min={1} style={{ width: 120 }} />
              </Form.Item>
              <Form.Item name="auto_fetch_interval_unit" noStyle>
                <Select style={{ width: 80 }} options={[
                  { label: '分钟', value: 'minutes' },
                  { label: '小时', value: 'hours' },
                  { label: '天', value: 'days' }
                ]} />
              </Form.Item>
            </Space.Compact>
          </Form.Item>

          {/* ── 钉钉机器人配置 (ReadHub专属) ── */}
          <Divider orientation="left">ReadHub 专属钉钉机器人</Divider>
          <Alert
            message="专属机器人说明"
            description="您可以为 ReadHub 配置一个独立的钉钉机器人，用于专门推送 RSS 文章，与 TaskTree 主机器人区分开。"
            type="info"
            showIcon
            style={{ marginBottom: 20 }}
          />
          <Form.Item
            label="启用 Stream 模式"
            name="dingtalk_stream_enabled"
            valuePropName="checked"
            tooltip="推荐！无需公网 IP 即可接收钉钉指令"
          >
            <Switch />
          </Form.Item>

          {streamEnabled ? (
            <>
              <Form.Item
                label="钉钉 Client ID"
                name="dingtalk_client_id"
                tooltip="在钉钉开发者后台获取的 AppKey / Client ID"
              >
                <Input placeholder="输入 Client ID" />
              </Form.Item>
              <Form.Item
                label="钉钉 Client Secret"
                name="dingtalk_client_secret"
                tooltip="在钉钉开发者后台获取的 AppSecret / Client Secret"
              >
                <Input.Password placeholder="输入 Client Secret (留空表示不修改)" />
              </Form.Item>
            </>
          ) : (
            <>
              <Form.Item
                label="钉钉 Webhook 地址"
                name="dingtalk_webhook"
                tooltip="机器人设置中的 Webhook URL"
              >
                <Input placeholder="https://oapi.dingtalk.com/robot/send?access_token=..." />
              </Form.Item>
              <Form.Item
                label="钉钉密钥（加签）"
                name="dingtalk_secret"
                tooltip="如果安全设置选择了加签，请填入密钥"
              >
                <Input.Password placeholder="SEC..." />
              </Form.Item>
            </>
          )}

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
