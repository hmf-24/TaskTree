import { useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import {
  AppstoreOutlined,
  ReadOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import TopBar from '../../components/layout/TopBar';

interface AppTile {
  id: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  path: string;
  gradient: string;
  available: boolean;
}

const APPS: AppTile[] = [
  {
    id: 'tasktree',
    name: 'TaskTree',
    description: '任务与项目执行',
    icon: <AppstoreOutlined />,
    path: '/app/tasktree',
    gradient: 'linear-gradient(135deg, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0.04) 100%)',
    available: true,
  },
  {
    id: 'readhub',
    name: 'ReadHub',
    description: 'RSS 资讯与知识转化',
    icon: <ReadOutlined />,
    path: '/app/readhub',
    gradient: 'linear-gradient(135deg, rgba(100,180,255,0.10) 0%, rgba(100,180,255,0.03) 100%)',
    available: true,
  },
  {
    id: 'settings',
    name: '设置',
    description: '账号、提醒与系统配置',
    icon: <SettingOutlined />,
    path: '/settings',
    gradient: 'linear-gradient(135deg, rgba(180,180,180,0.10) 0%, rgba(180,180,180,0.03) 100%)',
    available: true,
  },
];

export default function Launcher() {
  const navigate = useNavigate();

  return (
    <div style={{ minHeight: '100vh', background: 'var(--color-canvas)' }}>
      <Helmet><title>工作台 - Nexus</title></Helmet>

      <TopBar />

      <div style={{
        maxWidth: 900,
        margin: '0 auto',
        padding: '80px 24px 48px',
      }}>
        {/* 欢迎语 */}
        <div style={{ marginBottom: 48, textAlign: 'center' }}>
          <h1 style={{
            fontSize: 32,
            fontWeight: 700,
            color: 'var(--color-ink)',
            letterSpacing: '-0.03em',
            margin: '0 0 8px',
            fontFamily: 'var(--font-sans)',
          }}>
            Nexus
          </h1>
          <p style={{
            fontSize: 15,
            color: 'var(--color-ink-secondary)',
            margin: 0,
            letterSpacing: '0.01em',
          }}>
            选择一个工具开始工作
          </p>
        </div>

        {/* 方块网格 */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
          gap: 20,
        }}>
          {APPS.map((app) => (
            <div
              key={app.id}
              className={`launcher-card ${!app.available ? 'launcher-card--disabled' : ''}`}
              onClick={() => app.available && navigate(app.path)}
              style={{
                background: app.gradient,
                cursor: app.available ? 'pointer' : 'not-allowed',
                opacity: app.available ? 1 : 0.5,
              }}
            >
              {/* 图标 */}
              <div className="launcher-card__icon">
                {app.icon}
              </div>

              {/* 名称 */}
              <h3 className="launcher-card__name">
                {app.name}
              </h3>

              {/* 描述 */}
              <p className="launcher-card__desc">
                {app.description}
              </p>

              {/* 即将上线标记 */}
              {!app.available && (
                <span className="launcher-card__badge">
                  即将上线
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
