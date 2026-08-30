import React, { useMemo } from 'react'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { MapPin, Globe, Shield } from 'lucide-react'
import { useGraphStore } from '../../stores/useGraphStore'
import { useProjectStore } from '../../stores/useProjectStore'
import { useThemeStore } from '../../stores/useThemeStore'
import { ConfidenceBadge } from '../../components/ui/ConfidenceBadge'
import { EmptyState } from '../../components/ui/EmptyState'

// Custom marker icon
const customIcon = L.divIcon({
  className: 'custom-map-marker',
  html: `<div style="background-color: #4f9dff; width: 14px; height: 14px; border-radius: 50%; border: 2px solid #ffffff; box-shadow: 0 2px 6px rgba(0,0,0,0.3);"></div>`,
  iconSize: [14, 14],
  iconAnchor: [7, 7],
})

interface GeoEntity {
  id: string
  label: string
  type: string
  lat: number
  lng: number
  confidence: number
  country?: string
  city?: string
  org?: string
}

export const MapTab: React.FC = () => {
  const { nodes, setSelectedEntity } = useGraphStore()
  const { activeProject, setActiveTab, setIsNewModalOpen } = useProjectStore()
  const { resolved } = useThemeStore()

  // Extract geolocated entities from node properties
  const geoEntities: GeoEntity[] = useMemo(() => {
    const list: GeoEntity[] = []
    nodes.forEach((node) => {
      const props = node.data.properties || {}
      let lat = props.latitude || props.lat || props.loc?.split(',')[0]
      let lng = props.longitude || props.lng || props.lon || props.loc?.split(',')[1]

      if (lat && lng) {
        const numLat = parseFloat(lat)
        const numLng = parseFloat(lng)
        if (!isNaN(numLat) && !isNaN(numLng)) {
          list.push({
            id: node.data.id,
            label: node.data.label || node.data.id,
            type: node.data.type,
            lat: numLat,
            lng: numLng,
            confidence: node.data.confidence || 1.0,
            country: props.country || props.country_name,
            city: props.city,
            org: props.org || props.isp || props.asn,
          })
        }
      }
    })
    return list
  }, [nodes])

  // CartoDB Tile URL
  const tileUrl =
    resolved === 'dark'
      ? 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
      : 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png'

  if (!activeProject) {
    return (
      <EmptyState
        icon={Shield}
        title="No active project"
        description="Select or start an investigation to explore geolocated infrastructure."
        action={{ label: 'New Investigation', onClick: () => setIsNewModalOpen(true) }}
      />
    )
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden relative select-none">
      {/* Header bar */}
      <div className="p-3 bg-bg-surface border-b border-border-subtle flex items-center justify-between z-10">
        <div className="flex items-center gap-2">
          <MapPin className="w-4 h-4 text-accent" strokeWidth={1.5} />
          <h3 className="text-xs font-semibold text-text-primary">Infrastructure Geolocation</h3>
          <span className="text-2xs text-text-tertiary font-mono-data">
            ({geoEntities.length} mapped assets)
          </span>
        </div>
        <span className="text-[11px] text-text-tertiary">CartoDB Muted Basemap</span>
      </div>

      {/* Map or Empty State */}
      {geoEntities.length === 0 ? (
        <div className="flex-1 flex items-center justify-center bg-bg-canvas">
          <EmptyState
            icon={Globe}
            title="No geolocated assets found"
            description="Run DNS, IP lookup, or ASN inspection tools to discover geographic locations of target infrastructure."
          />
        </div>
      ) : (
        <div className="flex-1 relative">
          <MapContainer
            center={[geoEntities[0].lat, geoEntities[0].lng]}
            zoom={3}
            scrollWheelZoom={true}
            style={{ height: '100%', width: '100%' }}
          >
            <TileLayer
              attribution='&copy; <a href="https://carto.com/">CARTO</a>'
              url={tileUrl}
            />

            {geoEntities.map((item) => (
              <Marker
                key={item.id}
                position={[item.lat, item.lng]}
                icon={customIcon}
              >
                <Popup className="custom-popup">
                  <div className="p-2 min-w-[200px] space-y-1.5 text-2xs font-sans">
                    <div className="flex items-center justify-between gap-2 border-b border-border-subtle pb-1">
                      <span className="font-semibold text-accent uppercase text-[10px]">
                        {item.type}
                      </span>
                      <ConfidenceBadge score={item.confidence} size="sm" />
                    </div>
                    <p className="font-bold text-text-primary font-mono-data truncate">{item.id}</p>
                    {(item.city || item.country) && (
                      <p className="text-text-secondary">
                        Location: {[item.city, item.country].filter(Boolean).join(', ')}
                      </p>
                    )}
                    {item.org && (
                      <p className="text-text-secondary truncate">
                        Org: {item.org}
                      </p>
                    )}
                    <button
                      onClick={() => {
                        useProjectStore.getState().setSelectedEntityId(item.id)
                        setActiveTab('graph')
                      }}
                      className="w-full mt-2 py-1 px-2 text-center rounded bg-accent text-white font-medium hover:bg-accent-hover transition-colors text-[11px]"
                    >
                      View in Graph
                    </button>
                  </div>
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        </div>
      )}
    </div>
  )
}
