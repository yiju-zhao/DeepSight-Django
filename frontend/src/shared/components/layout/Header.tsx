import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, X, ChevronDown, LogOut } from 'lucide-react';
import { useAuth } from '@/shared/hooks/useAuth';

const Header = () => {
    const [isScrolled, setIsScrolled] = useState(false);
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const [isDashboardDropdownOpen, setIsDashboardDropdownOpen] = useState(false);
    const location = useLocation();
    const { isAuthenticated, handleLogout } = useAuth();

    useEffect(() => {
        const handleScroll = () => {
            setIsScrolled(window.scrollY > 10);
        };

        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            const target = event.target as HTMLElement;
            if (!target.closest('.dashboard-dropdown-container')) {
                setIsDashboardDropdownOpen(false);
            }
        };

        document.addEventListener('click', handleClickOutside);
        return () => document.removeEventListener('click', handleClickOutside);
    }, []);

    const navLinks = [
        // Dashboard is now a dropdown
        { name: 'Dataset', path: '/dataset' },
        { name: 'Deepdive', path: '/deepdive' },
    ];

    const dashboardSubLinks = [
        { name: 'Overview', path: '/dashboard' },
        { name: 'Conference', path: '/dashboard/conference' },
    ];

    return (
        <header
            className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${isScrolled ? 'bg-white/90 backdrop-blur-md shadow-huawei-sm' : 'bg-transparent'
                }`}
            style={{ height: 'var(--header-height)' }}
        >
            <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 h-full flex items-center justify-between">
                {/* Logo */}
                <Link to="/" className="flex items-center space-x-2 group">
                    <div className="w-8 h-8 bg-black text-white flex items-center justify-center rounded-lg font-bold text-lg group-hover:bg-accent-red transition-colors duration-300">
                        D
                    </div>
                    <span className="text-xl font-bold tracking-tight text-foreground">DeepSight</span>
                </Link>

                {/* Desktop Navigation */}
                <nav className="hidden md:flex items-center space-x-8">
                    {/* Dashboard Dropdown */}
                    <div className="relative dashboard-dropdown-container">
                        <button
                            className={`flex items-center space-x-1 text-sm font-medium transition-colors duration-300 hover:text-accent-red ${location.pathname.startsWith('/dashboard') || location.pathname.startsWith('/conference')
                                ? 'text-accent-red'
                                : 'text-foreground/80'
                                }`}
                            onClick={() => setIsDashboardDropdownOpen(!isDashboardDropdownOpen)}
                        >
                            <span>Dashboard</span>
                            <ChevronDown size={16} className={`transition-transform duration-300 ${isDashboardDropdownOpen ? 'rotate-180' : ''}`} />
                        </button>

                        {/* Dropdown Menu */}
                        <div
                            className={`absolute top-full left-0 mt-2 w-48 bg-white rounded-lg shadow-huawei-md border border-gray-100 overflow-hidden transition-all duration-200 origin-top-left ${isDashboardDropdownOpen ? 'opacity-100 scale-100 translate-y-0' : 'opacity-0 scale-95 -translate-y-2 pointer-events-none'
                                }`}
                        >
                            <div className="py-1">
                                {dashboardSubLinks.map((link) => (
                                    <Link
                                        key={link.path}
                                        to={link.path}
                                        className={`block px-4 py-2 text-sm hover:bg-gray-50 hover:text-accent-red transition-colors ${location.pathname === link.path ? 'text-accent-red font-medium' : 'text-foreground/80'
                                            }`}
                                        onClick={() => setIsDashboardDropdownOpen(false)}
                                    >
                                        {link.name}
                                    </Link>
                                ))}
                            </div>
                        </div>
                    </div>

                    {navLinks.map((link) => (
                        <Link
                            key={link.path}
                            to={link.path}
                            className={`text-sm font-medium transition-colors duration-300 hover:text-accent-red ${location.pathname === link.path ? 'text-accent-red' : 'text-foreground/80'
                                }`}
                        >
                            {link.name}
                        </Link>
                    ))}
                </nav>

                {/* Auth Button */}
                <div className="hidden md:block">
                    {isAuthenticated ? (
                        <button
                            onClick={() => handleLogout()}
                            className="flex items-center space-x-2 px-5 py-2.5 bg-white text-foreground border border-gray-200 text-sm font-medium rounded-md hover:bg-gray-50 hover:text-accent-red hover:border-gray-300 transition-all duration-300"
                        >
                            <LogOut size={16} />
                            <span>Logout</span>
                        </button>
                    ) : (
                        <Link
                            to="/login"
                            className="px-5 py-2.5 bg-black text-white text-sm font-medium rounded-md hover:bg-accent-red transition-colors duration-300 shadow-huawei-subtle hover:shadow-huawei-md"
                        >
                            Get Started
                        </Link>
                    )}
                </div>

                {/* Mobile Menu Button */}
                <button
                    className="md:hidden p-2 text-foreground hover:text-accent-red transition-colors"
                    onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                >
                    {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
                </button>
            </div>

            {/* Mobile Menu */}
            {isMobileMenuOpen && (
                <div className="md:hidden absolute top-[var(--header-height)] left-0 right-0 bg-white shadow-huawei-lg border-t border-gray-100 animate-slide-up">
                    <div className="flex flex-col p-4 space-y-4">
                        <div className="px-4 py-2 font-medium text-gray-400 text-xs uppercase tracking-wider">Dashboard</div>
                        {dashboardSubLinks.map((link) => (
                            <Link
                                key={link.path}
                                to={link.path}
                                className="text-base font-medium text-foreground/80 hover:text-accent-red py-2 px-8 rounded-md hover:bg-gray-50 transition-all"
                                onClick={() => setIsMobileMenuOpen(false)}
                            >
                                {link.name}
                            </Link>
                        ))}

                        <div className="border-t border-gray-100 my-2"></div>

                        {navLinks.map((link) => (
                            <Link
                                key={link.path}
                                to={link.path}
                                className="text-base font-medium text-foreground/80 hover:text-accent-red py-2 px-4 rounded-md hover:bg-gray-50 transition-all"
                                onClick={() => setIsMobileMenuOpen(false)}
                            >
                                {link.name}
                            </Link>
                        ))}

                        <div className="pt-4 border-t border-gray-100">
                            {isAuthenticated ? (
                                <button
                                    onClick={() => {
                                        handleLogout();
                                        setIsMobileMenuOpen(false);
                                    }}
                                    className="flex items-center justify-center space-x-2 w-full px-5 py-3 bg-white text-foreground border border-gray-200 text-sm font-medium rounded-md hover:bg-gray-50 hover:text-accent-red"
                                >
                                    <LogOut size={16} />
                                    <span>Logout</span>
                                </button>
                            ) : (
                                <Link
                                    to="/login"
                                    className="block w-full text-center px-5 py-3 bg-black text-white text-sm font-medium rounded-md hover:bg-accent-red transition-colors"
                                    onClick={() => setIsMobileMenuOpen(false)}
                                >
                                    Get Started
                                </Link>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </header>
    );
};

export default Header;
