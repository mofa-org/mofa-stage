import axios from 'axios'

const API_URL = 'http://localhost:5002/api'

export const fetchDependencies = () => {
  return axios.get(`${API_URL}/system/dependencies`)
}

export const installDependency = (id) => {
  return axios.post(`${API_URL}/system/dependencies/install`, { id })
}

export const fetchSystemInfo = () => {
  return axios.get(`${API_URL}/system/info`)
}
