import React, { useState, useEffect } from 'react';

interface MobileNavProps {
  brandName?: string;
  menuItems: Array<{
    label: string;
    href: string;
    icon?: React.ReactNode;
  }>;
  className?: string;
}

export const MobileNav: React.FC<MobileNavProps> = ({
  brandName = 'Zakera',
  menuItems,
  className = '',
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    // Check if mobile
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);

    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  useEffect(() => {
    // Prevent body scroll when menu is open
    if (isOpen && isMobile) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }

    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen, isMobile]);

  const handleMenuItemClick = () => {
    if (isMobile) {
      setIsOpen(false);
    }
  };

  return (
    <nav className={`navbar ${className}`}>
      <div className="navbar-content">
        {/* Brand/Logo */}
        <div className="navbar-brand">
          <a href="/" style={{ textDecoration: 'none', color: 'inherit' }}>
            <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 'bold' }}>
              {brandName}
            </h1>
          </a>
        </div>

        {/* Mobile menu toggle */}
        <button
          className={`menu-toggle ${isOpen ? 'active' : ''}`}
          onClick={() => setIsOpen(!isOpen)}
          aria-label="Toggle menu"
          aria-expanded={isOpen}
        >
          <span className="menu-toggle-icon" />
        </button>

        {/* Navigation menu */}
        <div className={`mobile-menu ${isOpen ? 'active' : ''}`}>
          {/* Close button for mobile */}
          {isMobile && (
            <button
              className="menu-toggle active"
              onClick={() => setIsOpen(false)}
              style={{
                position: 'absolute',
                top: '1rem',
                right: '1rem',
              }}
              aria-label="Close menu"
            >
              <span className="menu-toggle-icon" />
            </button>
          )}

          <div className="mobile-menu-items">
            {menuItems.map((item, index) => (
              <a
                key={index}
                href={item.href}
                className="mobile-menu-item"
                onClick={handleMenuItemClick}
              >
                {item.icon && (
                  <span style={{ marginRight: '0.5rem' }}>{item.icon}</span>
                )}
                {item.label}
              </a>
            ))}
          </div>
        </div>
      </div>
    </nav>
  );
};
