import React from 'react';
import { Layout as AntLayout, Menu, Avatar, Dropdown } from 'antd';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { UserOutlined, LogoutOutlined, SettingOutlined, HomeOutlined } from '@ant-design/icons';
import { useAuthStore } from '../../stores/auth';
import NotificationPanel from '../notification/NotificationPanel';

const { Header, Sider, Content } = AntLayout;

export default function Layout() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();

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
        type: 'divider',
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

  return (
    <AntLayout className="min-h-screen">
      <Header className="flex justify-between items-center px-4 bg-white shadow-sm" style={{ zIndex: 1 }}>
        <div className="text-xl font-bold text-blue-600">TaskTree</div>
        <div className="flex items-center gap-4">
          <NotificationPanel />
          <Dropdown menu={userMenu} placement="bottomRight">
            <div className="flex items-center cursor-pointer">
              <Avatar icon={<UserOutlined />} src={user?.avatar} />
              <span className="ml-2">{user?.nickname || user?.email}</span>
            </div>
          </Dropdown>
        </div>
      </Header>
      <AntLayout>
        <Sider width={200} className="bg-white">
          <Menu
            mode="inline"
            selectedKeys={[location.pathname]}
            items={menuItems}
            onClick={({ key }) => navigate(key)}
            className="border-r-0"
          />
        </Sider>
        <Content className="bg-gray-100" style={{ minHeight: 'calc(100vh - 64px)' }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  );
}