import { CheckCircleIcon, AlertCircleIcon } from './Icons'

function Toast({ message, type = 'success' }) {
    return (
        <div className={`toast toast-${type}`}>
            {type === 'success' ? <CheckCircleIcon /> : <AlertCircleIcon />}
            {message}
        </div>
    )
}

export default Toast
