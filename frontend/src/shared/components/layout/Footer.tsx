import React from 'react';
import { Link } from 'react-router-dom';

const Footer = () => {
    return (
        <footer className="bg-gray-50 border-t border-gray-200 py-12">
            <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 flex flex-col items-center justify-center text-center">
                <Link to="/" className="flex items-center space-x-2 mb-4 group">
                    <div className="w-10 h-10 bg-black text-white flex items-center justify-center rounded-lg font-bold text-xl group-hover:bg-accent-red transition-colors duration-300">
                        D
                    </div>
                    <span className="text-2xl font-bold tracking-tight text-foreground">DeepSight</span>
                </Link>
                <p className="text-muted-foreground text-base max-w-md">
                    Empowering researchers and developers with advanced AI insights and deep learning analytics.
                </p>
            </div>
        </footer>
    );
};

export default Footer;
