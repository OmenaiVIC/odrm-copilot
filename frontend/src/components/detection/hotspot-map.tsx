'use client';

import 'leaflet/dist/leaflet.css';

import type { CSSProperties, ReactElement } from 'react';
import { MapContainer, Marker, Popup, TileLayer } from 'react-leaflet';

import type { Hotspot } from '@/lib/types';

export interface HotspotMapProps {
  hotspots: Hotspot[];
}

const MAP_CENTER: [number, number] = [4.8, 7.0];
const MAP_ZOOM = 10;
const MAP_STYLE: CSSProperties = { height: '400px', width: '100%' };

export default function HotspotMap({ hotspots }: HotspotMapProps): ReactElement {
  return (
    <div className="relative">
      {hotspots.length === 0 && (
        <p className="absolute left-1/2 top-2 z-[1000] -translate-x-1/2 rounded bg-white/90 px-3 py-1 text-sm text-gray-600 shadow">
          No hotspots in current view.
        </p>
      )}
      <MapContainer center={MAP_CENTER} zoom={MAP_ZOOM} style={MAP_STYLE}>
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="© OpenStreetMap contributors"
        />
        {hotspots.map((hotspot) => (
          <Marker key={hotspot.id} position={[hotspot.latitude, hotspot.longitude]}>
            <Popup>
              <div className="space-y-1 text-sm">
                <div>
                  <strong>ID:</strong> {hotspot.id}
                </div>
                <div>
                  <strong>Latitude:</strong> {hotspot.latitude}
                </div>
                <div>
                  <strong>Longitude:</strong> {hotspot.longitude}
                </div>
                <div>
                  <strong>Intensity:</strong> {hotspot.intensity_ppb} ppb
                </div>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}