import React, { useState } from 'react';
import { Layout as AntLayout, Menu, Avatar, Dropdown, Typography } from 'antd';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  UserOutlined, LogoutOutlined, SettingOutlined, HomeOutlined,
  MenuFoldOutlined, MenuUnfoldOutlined,
} from '@ant-design/icons';
import { useAuthStore } from '../../stores/auth';
import NotificationPanel from '../notification/NotificationPanel';

const { Header, Sider, Content } = AntLayout;
const { Text } = Typography;

export default function Layout() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

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

  const menuItems = [
    {
      key: '/',
      icon: <HomeOutlined />,
      label: '项目列表',
    },
    {
      key: '/settings',
      icon: <SettingOutlined />,
      label: '设置',
    },
  ];

  const siderWidth = collapsed ? 72 : 240;

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider
        width={240}
        collapsedWidth={72}
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        trigger={null}
        style={{
          background: 'var(--color-surface)',
          backdropFilter: 'var(--glass-blur)',
          WebkitBackdropFilter: 'var(--glass-blur)',
          borderRight: '1px solid var(--color-border)',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          zIndex: 10,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Logo */}
        <div
          style={{
            height: 'var(--header-height)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'flex-start',
            padding: collapsed ? '0' : '0 20px',
            borderBottom: '1px solid var(--color-border)',
            cursor: 'pointer',
            transition: 'padding 0.2s var(--ease-smooth)',
          }}
          onClick={() => navigate('/')}
        >
          {/* Logo Mark — 深灰纯色方块，取代紫蓝渐变 */}
          <div style={{
            width: 30, height: 30, borderRadius: 'var(--radius-button)',
            background: 'var(--color-brand)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0,
            transition: 'transform 0.2s var(--ease-smooth)',
          }}>
            <span style={{
              color: '#000', fontWeight: 700, fontSize: 14,
              fontFamily: 'var(--font-sans)',
              letterSpacing: '-0.02em',
            }}>T</span>
          </div>
          {!collapsed && (
            <span style={{
              marginLeft: 12, fontSize: 17, fontWeight: 600,
              color: 'var(--color-ink)',
              letterSpacing: '-0.02em',
              fontFamily: 'var(--font-sans)',
            }}>
              TaskTree
            </span>
          )}
        </div>

        {/* 导航菜单 */}
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ borderRight: 0, flex: 1, paddingTop: 8, background: 'transparent' }}
        />

        {/* 底部信息 */}
        <div style={{
          padding: collapsed ? '12px 8px' : '12px 16px',
          borderTop: '1px solid var(--color-border)',
          textAlign: 'center',
        }}>
          {!collapsed && (
            <Text
              style={{
                fontSize: 11,
                color: 'var(--color-ink-tertiary)',
                letterSpacing: '0.02em',
              }}
            >
              TaskTree v1.0.0
            </Text>
          )}
        </div>
      </Sider>

      <AntLayout style={{
        marginLeft: siderWidth,
        transition: 'margin-left 0.2s var(--ease-smooth)',
      }}>
        <Header style={{
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
          <div
            style={{
              cursor: 'pointer', fontSize: 16,
              color: 'var(--color-ink-tertiary)',
              padding: 4,
              borderRadius: 'var(--radius-button)',
              transition: 'color 0.15s var(--ease-smooth), background 0.15s var(--ease-smooth)',
            }}
            onClick={() => setCollapsed(!collapsed)}
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
        </Header>
        <Content style={{
          background: 'var(--color-canvas)',
          minHeight: 'calc(100vh - var(--header-height))',
        }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  );
}
