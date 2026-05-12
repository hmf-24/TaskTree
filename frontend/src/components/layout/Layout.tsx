import { useState } from 'react';
import { Layout as AntLayout, Menu, Typography } from 'antd';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { ProjectOutlined, SettingOutlined, ReadOutlined, AppstoreOutlined } from '@ant-design/icons';
import TopBar from './TopBar';

const { Sider, Content } = AntLayout;
const { Text } = Typography;

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  const isReadHub = location.pathname.startsWith('/app/readhub');
  const isTaskTree = location.pathname.startsWith('/app/tasktree');
  
  const appName = isReadHub ? 'ReadHub' : isTaskTree ? 'TaskTree' : 'Nexus';
  const appLetter = isReadHub ? 'R' : isTaskTree ? 'T' : 'N';

  const menuItems = isReadHub ? [
    {
      key: '/app/readhub',
      icon: <ReadOutlined />,
      label: '阅读中心',
    },
    {
      key: '/app/readhub/settings',
      icon: <SettingOutlined />,
      label: 'ReadHub 设置',
    },

    {
      type: 'divider',
    },
    {
      key: '/',
      icon: <AppstoreOutlined />,
      label: '返回工作台',
    },
  ] : [
    {
      key: '/app/tasktree',
      icon: <ProjectOutlined />,
      label: '项目列表',
    },

    {
      type: 'divider',
    },
    {
      key: '/',
      icon: <AppstoreOutlined />,
      label: '返回工作台',
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
        {/* Logo — 点击返回工作台首页 */}
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
          onClick={() => navigate(isReadHub ? '/app/readhub' : isTaskTree ? '/app/tasktree' : '/')}
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
            }}>{appLetter}</span>
          </div>
          {!collapsed && (
            <span style={{
              marginLeft: 12, fontSize: 17, fontWeight: 600,
              color: 'var(--color-ink)',
              letterSpacing: '-0.02em',
              fontFamily: 'var(--font-sans)',
            }}>
              {appName}
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
              Nexus v1.0.0
            </Text>
          )}
        </div>
      </Sider>

      <AntLayout style={{
        marginLeft: siderWidth,
        transition: 'margin-left 0.2s var(--ease-smooth)',
      }}>
        <TopBar
          showSidebarToggle
          collapsed={collapsed}
          onToggleCollapse={() => setCollapsed(!collapsed)}
        />
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
