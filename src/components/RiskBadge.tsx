import React from 'react';

interface RiskBadgeProps {
    level: 'LOW' | 'MEDIUM' | 'HIGH' | 'UNLIMITED';
    maxLoss?: string;
    showDetails?: boolean;
}

const RiskBadge: React.FC<RiskBadgeProps> = ({ level, maxLoss, showDetails = false }) => {
    const config = {
        LOW: {
            icon: '🟢',
            color: 'bg-green-100 text-green-800 border-green-300',
            label: 'Baixo Risco'
        },
        MEDIUM: {
            icon: '🟡',
            color: 'bg-yellow-100 text-yellow-800 border-yellow-300',
            label: 'Risco Moderado'
        },
        HIGH: {
            icon: '🔴',
            color: 'bg-red-100 text-red-800 border-red-300',
            label: 'Alto Risco'
        },
        UNLIMITED: {
            icon: '🚨',
            color: 'bg-purple-100 text-purple-800 border-purple-300',
            label: 'Risco Ilimitado'
        }
    };

    const { icon, color, label } = config[level];

    return (
        <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border ${color} text-xs font-medium`}>
            <span>{icon}</span>
            <span>{label}</span>
            {showDetails && maxLoss && (
                <span className="ml-1 opacity-75">• {maxLoss}</span>
            )}
        </div>
    );
};

export default RiskBadge;
