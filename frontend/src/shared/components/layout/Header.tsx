import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, X } from 'lucide-react';

const Header = () => {
    const [isScrolled, setIsScrolled] = useState(false);
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const location = useLocation();

    useEffect(() => {
        const handleScroll = () => {
            setIsScrolled(window.scrollY > 10);
        };

        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    const navLinks = [
        { name: 'Dashboard', path: '/dashboard' },
        { name: 'Dataset', path: '/dataset' },
        { name: 'Deepdive', path: '/deepdive' },
        { name: 'Conference', path: '/conference' },
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

                {/* CTA Button */}
                <div className="hidden md:block">
                    <Link
                        to="/login"
                        className="px-5 py-2.5 bg-black text-white text-sm font-medium rounded-md hover:bg-accent-red transition-colors duration-300 shadow-huawei-subtle hover:shadow-huawei-md"
                    >
                        Get Started
                    </Link>
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
                            <Link
                                to="/login"
                                className="block w-full text-center px-5 py-3 bg-black text-white text-sm font-medium rounded-md hover:bg-accent-red transition-colors"
                                onClick={() => setIsMobileMenuOpen(false)}
                            >
                                Get Started
                            </Link>
                        </div>
                    </div>
                </div>
            )}
        </header>
    );
};

export default Header;
