import { Avatar, Dropdown } from 'antd';
import { useNavigate } from 'react-router-dom';
import {
  UserOutlined, LogoutOutlined, SettingOutlined,
  MenuFoldOutlined, MenuUnfoldOutlined,
} from '@ant-design/icons';
import { useAuthStore } from '../../stores/auth';
import NotificationPanel from '../notification/NotificationPanel';

interface TopBarProps {
  /** 是否显示侧边栏折叠按钮 */
  showSidebarToggle?: boolean;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

export default function TopBar({
  showSidebarToggle = false,
  collapsed = false,
  onToggleCollapse,
}: TopBarProps) {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/auth/login');
  };

  const userMenu = {
    items: [
      {
        key: 'profile',
        label: '个人资料',
        icon: <UserOutlined />,
        onClick: () => navigate('/settings'),
      },
      {
        key: 'settings',
        label: '设置',
        icon: <SettingOutlined />,
        onClick: () => navigate('/settings'),
      },
      {
        type: 'divider' as const,
      },
      {
        key: 'logout',
        label: '退出登录',
        icon: <LogoutOutlined />,
        onClick: handleLogout,
        danger: true,
      },
    ],
  };

  return (
    <header style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '0 24px',
      background: 'var(--color-surface)',
      backdropFilter: 'var(--glass-blur)',
      WebkitBackdropFilter: 'var(--glass-blur)',
      borderBottom: '1px solid var(--color-border)',
      position: 'sticky',
      top: 0,
      zIndex: 9,
      height: 'var(--header-height)',
      lineHeight: 'var(--header-height)',
    }}>
      <div>
        {showSidebarToggle && (
          <div
            style={{
              cursor: 'pointer', fontSize: 16,
              color: 'var(--color-ink-tertiary)',
              padding: 4,
              borderRadius: 'var(--radius-button)',
              transition: 'color 0.15s var(--ease-smooth), background 0.15s var(--ease-smooth)',
              display: 'inline-flex',
              alignItems: 'center',
            }}
            onClick={onToggleCollapse}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLDivElement).style.color = 'var(--color-ink)';
              (e.currentTarget as HTMLDivElement).style.background = 'var(--color-surface-active)';
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLDivElement).style.color = 'var(--color-ink-tertiary)';
              (e.currentTarget as HTMLDivElement).style.background = 'transparent';
            }}
          >
            {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          </div>
        )}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <NotificationPanel />
        <Dropdown menu={userMenu} placement="bottomRight">
          <div style={{
            display: 'flex', alignItems: 'center', cursor: 'pointer', gap: 8,
            padding: '4px 8px',
            borderRadius: 'var(--radius-button)',
            transition: 'background 0.15s var(--ease-smooth)',
          }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLDivElement).style.background = 'var(--color-surface-active)';
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLDivElement).style.background = 'transparent';
            }}
          >
            <Avatar
              size={28}
              icon={<UserOutlined />}
              src={user?.avatar}
              style={{
                background: 'var(--color-brand)',
                fontSize: 12,
              }}
            />
            <span style={{
              fontWeight: 500, fontSize: 13,
              color: 'var(--color-ink)',
            }}>
              {user?.nickname || user?.email}
            </span>
          </div>
        </Dropdown>
      </div>
    </header>
  );
}
