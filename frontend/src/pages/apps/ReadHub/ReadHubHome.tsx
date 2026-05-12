import { useState, useEffect, useCallback } from 'react';
import {
  Input, Button, Modal, Form, Empty, Spin, Badge, message, Tooltip, Select, Space,
} from 'antd';
import {
  PlusOutlined, ReloadOutlined, DeleteOutlined,
  ReadOutlined, CheckOutlined, LinkOutlined,
  DownloadOutlined, FileMarkdownOutlined, SwitcherOutlined,
} from '@ant-design/icons';
import { Helmet } from 'react-helmet-async';
import { feedsAPI, articlesAPI } from '../../../api/readhub';
import { projectsAPI } from '../../../api/index';

interface Feed {
  id: number;
  url: string;
  name: string;
  is_active: boolean;
  last_fetched_at: string | null;
}

interface Article {
  id: number;
  feed_id: number;
  title: string;
  summary: string | null;
  source_url: string;
  author: string | null;
  published_at: string | null;
  is_read: boolean;
  is_saved_to_obsidian: boolean;
}

interface ArticleDetail extends Article {
  content_html: string | null;
}

export default function ReadHubHome() {
  const [feeds, setFeeds] = useState<Feed[]>([]);
  const [articles, setArticles] = useState<Article[]>([]);
  const [totalArticles, setTotalArticles] = useState(0);
  const [selectedFeedId, setSelectedFeedId] = useState<number | null>(null);
  const [selectedArticle, setSelectedArticle] = useState<ArticleDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [page, setPage] = useState(1);
  const [form] = Form.useForm();
  // 操作状态
  const [savingToObsidian, setSavingToObsidian] = useState(false);
  const [convertModalOpen, setConvertModalOpen] = useState(false);
  const [converting, setConverting] = useState(false);
  const [projects, setProjects] = useState<{id: number; name: string}[]>([]);
  const [convertProjectId, setConvertProjectId] = useState<number | null>(null);

  // 加载订阅源列表
  const loadFeeds = useCallback(async () => {
    try {
      const res: any = await feedsAPI.list();
      if (res.code === 200) setFeeds(res.data);
    } catch (e: any) {
      message.error(e.message || '加载订阅源失败');
    }
  }, []);

  // 加载文章列表
  const loadArticles = useCallback(async (feedId?: number | null, p?: number) => {
    setLoading(true);
    try {
      const res: any = await articlesAPI.list({
        feed_id: feedId ?? undefined,
        page: p ?? page,
        page_size: 30,
      });
      if (res.code === 200) {
        setArticles(res.data.items);
        setTotalArticles(res.data.total);
      }
    } catch (e: any) {
      message.error(e.message || '加载文章失败');
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => { loadFeeds(); }, [loadFeeds]);
  useEffect(() => { loadArticles(selectedFeedId, page); }, [selectedFeedId, page]);

  // 手动拉取
  const handleFetch = async () => {
    setFetching(true);
    try {
      const res: any = await feedsAPI.fetch();
      if (res.code === 200) {
        const d = res.data;
        message.success(`拉取完成：${d.total_new} 篇新文章`);
        if (d.errors?.length > 0) {
          d.errors.forEach((e: string) => message.warning(e));
        }
        loadArticles(selectedFeedId, 1);
        setPage(1);
      }
    } catch (e: any) {
      message.error(e.message || '拉取失败');
    } finally {
      setFetching(false);
    }
  };

  // 添加订阅源
  const handleAddFeed = async (values: { url: string; name: string }) => {
    try {
      const res: any = await feedsAPI.add(values);
      if (res.code === 200) {
        message.success('订阅源添加成功');
        setAddModalOpen(false);
        form.resetFields();
        loadFeeds();
      }
    } catch (e: any) {
      message.error(e.message || '添加失败');
    }
  };

  // 删除订阅源
  const handleDeleteFeed = (feed: Feed) => {
    Modal.confirm({
      title: '删除订阅源',
      content: `确定删除「${feed.name}」及其所有文章吗？`,
      onOk: async () => {
        try {
          const res: any = await feedsAPI.delete(feed.id);
          if (res.code === 200) {
            message.success('已删除');
            loadFeeds();
            if (selectedFeedId === feed.id) {
              setSelectedFeedId(null);
            }
          }
        } catch (e: any) {
          message.error(e.message || '删除失败');
        }
      },
    });
  };

  // 查看文章详情
  const handleArticleClick = async (article: Article) => {
    try {
      const res: any = await articlesAPI.detail(article.id);
      if (res.code === 200) {
        setSelectedArticle(res.data);
        // 更新列表中的已读状态
        setArticles((prev) =>
          prev.map((a) => (a.id === article.id ? { ...a, is_read: true } : a))
        );
      }
    } catch (e: any) {
      message.error(e.message || '加载文章详情失败');
    }
  };

  return (
    <div className="page-container" style={{ display: 'flex', gap: 24, minHeight: 'calc(100vh - var(--header-height))' }}>
      <Helmet><title>ReadHub - Nexus</title></Helmet>

      {/* ─── 左侧：订阅源列表 ─── */}
      <div style={{
        width: 240, flexShrink: 0,
        display: 'flex', flexDirection: 'column', gap: 8,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-ink-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            订阅源
          </span>
          <div style={{ display: 'flex', gap: 4 }}>
            <Tooltip title="拉取最新">
              <Button type="text" size="small" icon={<ReloadOutlined spin={fetching} />} onClick={handleFetch} loading={fetching} />
            </Tooltip>
            <Tooltip title="添加订阅源">
              <Button type="text" size="small" icon={<PlusOutlined />} onClick={() => setAddModalOpen(true)} />
            </Tooltip>
          </div>
        </div>

        {/* 全部 */}
        <div
          style={{
            padding: '8px 12px', borderRadius: 'var(--radius-button)', cursor: 'pointer',
            background: selectedFeedId === null ? 'var(--color-surface-active)' : 'transparent',
            color: selectedFeedId === null ? 'var(--color-ink)' : 'var(--color-ink-secondary)',
            fontSize: 13, fontWeight: selectedFeedId === null ? 500 : 400,
            transition: 'all 0.15s var(--ease-smooth)',
          }}
          onClick={() => { setSelectedFeedId(null); setPage(1); }}
        >
          全部文章
        </div>

        {feeds.map((feed) => (
          <div
            key={feed.id}
            style={{
              padding: '8px 12px', borderRadius: 'var(--radius-button)', cursor: 'pointer',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              background: selectedFeedId === feed.id ? 'var(--color-surface-active)' : 'transparent',
              color: selectedFeedId === feed.id ? 'var(--color-ink)' : 'var(--color-ink-secondary)',
              fontSize: 13, fontWeight: selectedFeedId === feed.id ? 500 : 400,
              transition: 'all 0.15s var(--ease-smooth)',
            }}
            onClick={() => { setSelectedFeedId(feed.id); setPage(1); }}
          >
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{feed.name}</span>
            <DeleteOutlined
              style={{ fontSize: 12, color: 'var(--color-ink-tertiary)', flexShrink: 0 }}
              onClick={(e) => { e.stopPropagation(); handleDeleteFeed(feed); }}
            />
          </div>
        ))}

        {feeds.length === 0 && (
          <div style={{ padding: '24px 0', textAlign: 'center', color: 'var(--color-ink-tertiary)', fontSize: 12 }}>
            暂无订阅源
          </div>
        )}
      </div>

      {/* ─── 中间：文章列表 ─── */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 13, color: 'var(--color-ink-tertiary)' }}>
            共 {totalArticles} 篇文章
          </span>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: 48 }}><Spin /></div>
        ) : articles.length === 0 ? (
          <Empty description="暂无文章，点击左上角拉取最新内容" />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {articles.map((article) => (
              <div
                key={article.id}
                style={{
                  padding: '12px 16px',
                  borderRadius: 'var(--radius-button)',
                  cursor: 'pointer',
                  background: selectedArticle?.id === article.id ? 'var(--color-surface-active)' : 'transparent',
                  transition: 'background 0.15s var(--ease-smooth)',
                  borderLeft: selectedArticle?.id === article.id ? '2px solid var(--color-brand)' : '2px solid transparent',
                }}
                onClick={() => handleArticleClick(article)}
                onMouseEnter={(e) => { if (selectedArticle?.id !== article.id) (e.currentTarget as HTMLDivElement).style.background = 'var(--color-surface-hover)'; }}
                onMouseLeave={(e) => { if (selectedArticle?.id !== article.id) (e.currentTarget as HTMLDivElement).style.background = 'transparent'; }}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                  {!article.is_read && (
                    <Badge dot color="rgba(100,180,255,0.9)" style={{ marginTop: 6 }} />
                  )}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontSize: 14, fontWeight: article.is_read ? 400 : 500,
                      color: article.is_read ? 'var(--color-ink-secondary)' : 'var(--color-ink)',
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>
                      {article.title}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--color-ink-tertiary)', marginTop: 4 }}>
                      {article.author && <span>{article.author} · </span>}
                      {article.published_at ? new Date(article.published_at).toLocaleDateString('zh-CN') : ''}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* 简单分页 */}
        {totalArticles > 30 && (
          <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 16 }}>
            <Button disabled={page <= 1} onClick={() => setPage(page - 1)}>上一页</Button>
            <span style={{ lineHeight: '32px', color: 'var(--color-ink-tertiary)', fontSize: 13 }}>
              第 {page} 页
            </span>
            <Button disabled={articles.length < 30} onClick={() => setPage(page + 1)}>下一页</Button>
          </div>
        )}
      </div>

      {/* ─── 右侧：文章详情 ─── */}
      {selectedArticle && (
        <div style={{
          width: 480, flexShrink: 0, overflow: 'auto',
          padding: '0 0 0 24px',
          borderLeft: '1px solid var(--color-border)',
          maxHeight: 'calc(100vh - var(--header-height) - 56px)',
        }}>
          <div style={{ marginBottom: 16 }}>
            <h2 style={{
              fontSize: 20, fontWeight: 600, lineHeight: 1.4,
              color: 'var(--color-ink)', marginBottom: 8,
            }}>
              {selectedArticle.title}
            </h2>
            <div style={{ display: 'flex', gap: 12, fontSize: 12, color: 'var(--color-ink-tertiary)' }}>
              {selectedArticle.author && <span>{selectedArticle.author}</span>}
              {selectedArticle.published_at && <span>{new Date(selectedArticle.published_at).toLocaleString('zh-CN')}</span>}
              <a href={selectedArticle.source_url} target="_blank" rel="noopener noreferrer"
                style={{ color: 'var(--color-ink-tertiary)', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                <LinkOutlined /> 原文
              </a>
            </div>
          </div>

          {/* 操作按钮栏 */}
          <div style={{
            display: 'flex', gap: 8, marginBottom: 16,
            padding: '10px 0',
            borderBottom: '1px solid var(--color-border)',
          }}>
            <Tooltip title={selectedArticle.is_saved_to_obsidian ? '已保存到 Obsidian' : '保存到 Obsidian'}>
              <Button
                size="small"
                type={selectedArticle.is_saved_to_obsidian ? 'default' : 'primary'}
                ghost={!selectedArticle.is_saved_to_obsidian}
                icon={selectedArticle.is_saved_to_obsidian ? <CheckOutlined /> : <FileMarkdownOutlined />}
                loading={savingToObsidian}
                disabled={selectedArticle.is_saved_to_obsidian}
                onClick={async () => {
                  setSavingToObsidian(true);
                  try {
                    const res: any = await articlesAPI.saveToObsidian(selectedArticle.id);
                    if (res.code === 200) {
                      message.success('已保存到 Obsidian');
                      setSelectedArticle({ ...selectedArticle, is_saved_to_obsidian: true });
                      setArticles(prev => prev.map(a => a.id === selectedArticle.id ? { ...a, is_saved_to_obsidian: true } : a));
                    }
                  } catch (e: any) {
                    message.error(e.detail || e.message || '保存失败');
                  } finally {
                    setSavingToObsidian(false);
                  }
                }}
              >
                {selectedArticle.is_saved_to_obsidian ? '已保存' : 'Obsidian'}
              </Button>
            </Tooltip>
            <Tooltip title="将文章转化为 TaskTree 任务">
              <Button
                size="small"
                icon={<SwitcherOutlined />}
                onClick={async () => {
                  // 加载项目列表
                  try {
                    const res: any = await projectsAPI.list();
                    if (res.code === 200) {
                      setProjects(res.data.items || res.data || []);
                    }
                  } catch (e) {
                    // ignore
                  }
                  setConvertModalOpen(true);
                }}
              >
                转为任务
              </Button>
            </Tooltip>
          </div>
          <div
            className="prose-bubble"
            dangerouslySetInnerHTML={{ __html: selectedArticle.content_html || '<p>暂无正文内容</p>' }}
          />
        </div>
      )}

      {/* ─── 添加订阅源弹窗 ─── */}
      <Modal
        title="添加订阅源"
        open={addModalOpen}
        onCancel={() => setAddModalOpen(false)}
        onOk={() => form.submit()}
      >
        <Form form={form} layout="vertical" onFinish={handleAddFeed}>
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入订阅源名称' }]}>
            <Input placeholder="例如：阮一峰的博客" />
          </Form.Item>
          <Form.Item name="url" label="Feed URL" rules={[{ required: true, message: '请输入 RSS Feed 地址' }]}>
            <Input placeholder="https://your-wewerss.com/feeds/xxx.xml" />
          </Form.Item>
        </Form>
      </Modal>

      {/* ─── 转为任务弹窗 ─── */}
      <Modal
        title="将文章转为任务"
        open={convertModalOpen}
        onCancel={() => setConvertModalOpen(false)}
        confirmLoading={converting}
        onOk={async () => {
          if (!convertProjectId) {
            message.warning('请选择目标项目');
            return;
          }
          if (!selectedArticle) return;
          setConverting(true);
          try {
            const res: any = await articlesAPI.convertToTask(selectedArticle.id, { project_id: convertProjectId });
            if (res.code === 200) {
              message.success(res.message || '任务创建成功');
              setConvertModalOpen(false);
            } else {
              message.error(res.message || '创建失败');
            }
          } catch (e: any) {
            message.error(e.detail || e.message || '创建失败');
          } finally {
            setConverting(false);
          }
        }}
      >
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 13, color: 'var(--color-ink-secondary)', marginBottom: 8 }}>文章标题</div>
          <div style={{ fontSize: 15, fontWeight: 500 }}>{selectedArticle?.title}</div>
        </div>
        <div>
          <div style={{ fontSize: 13, color: 'var(--color-ink-secondary)', marginBottom: 8 }}>目标项目</div>
          <Select
            style={{ width: '100%' }}
            placeholder="选择项目"
            value={convertProjectId}
            onChange={(v) => setConvertProjectId(v)}
            options={projects.map(p => ({ label: p.name, value: p.id }))}
          />
        </div>
      </Modal>
    </div>
  );
}
