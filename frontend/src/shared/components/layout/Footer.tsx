import React from 'react';
import { Link } from 'react-router-dom';
import { Github, Twitter, Linkedin } from 'lucide-react';

const Footer = () => {
    const currentYear = new Date().getFullYear();

    const footerLinks = {
        Product: [
            { name: 'Dashboard', path: '/dashboard' },
            { name: 'Dataset', path: '/dataset' },
            { name: 'Deepdive', path: '/deepdive' },
            { name: 'Conference', path: '/conference' },
        ],
        Resources: [
            { name: 'Documentation', path: '/docs' },
            { name: 'API Reference', path: '/api' },
            { name: 'Blog', path: '/blog' },
            { name: 'Community', path: '/community' },
        ],
        Company: [
            { name: 'About', path: '/about' },
            { name: 'Careers', path: '/careers' },
            { name: 'Contact', path: '/contact' },
            { name: 'Privacy', path: '/privacy' },
        ],
    };

    return (
        <footer className="bg-gray-50 border-t border-gray-200 pt-16 pb-8">
            <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-12 mb-12">
                    {/* Brand Column */}
                    <div className="lg:col-span-2">
                        <Link to="/" className="flex items-center space-x-2 mb-4">
                            <div className="w-8 h-8 bg-black text-white flex items-center justify-center rounded-lg font-bold text-lg">
                                D
                            </div>
                            <span className="text-xl font-bold tracking-tight text-foreground">DeepSight</span>
                        </Link>
                        <p className="text-muted-foreground text-sm leading-relaxed max-w-xs mb-6">
                            Empowering researchers and developers with advanced AI insights and deep learning analytics.
                        </p>
                        <div className="flex space-x-4">
                            <a href="#" className="text-gray-400 hover:text-black transition-colors">
                                <Github size={20} />
                            </a>
                            <a href="#" className="text-gray-400 hover:text-black transition-colors">
                                <Twitter size={20} />
                            </a>
                            <a href="#" className="text-gray-400 hover:text-black transition-colors">
                                <Linkedin size={20} />
                            </a>
                        </div>
                    </div>

                    {/* Links Columns */}
                    {Object.entries(footerLinks).map(([category, links]) => (
                        <div key={category}>
                            <h3 className="font-bold text-foreground mb-4">{category}</h3>
                            <ul className="space-y-3">
                                {links.map((link) => (
                                    <li key={link.name}>
                                        <Link
                                            to={link.path}
                                            className="text-sm text-muted-foreground hover:text-accent-red transition-colors"
                                        >
                                            {link.name}
                                        </Link>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    ))}
                </div>

                {/* Bottom Bar */}
                <div className="pt-8 border-t border-gray-200 flex flex-col md:flex-row justify-between items-center">
                    <p className="text-sm text-muted-foreground mb-4 md:mb-0">
                        © {currentYear} DeepSight. All rights reserved.
                    </p>
                    <div className="flex space-x-6">
                        <Link to="/terms" className="text-sm text-muted-foreground hover:text-black transition-colors">
                            Terms
                        </Link>
                        <Link to="/privacy" className="text-sm text-muted-foreground hover:text-black transition-colors">
                            Privacy
                        </Link>
                        <Link to="/cookies" className="text-sm text-muted-foreground hover:text-black transition-colors">
                            Cookies
                        </Link>
                    </div>
                </div>
            </div>
        </footer>
    );
};

export default Footer;
