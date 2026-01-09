# ... (Mantenemos la estructura anterior)

        # 3. LÓGICA DE REJILLAS (GRID) MEJORADA
        evento = "VIGILANDO"
        
        # Abrir el primer nivel si no hay nada
        if not st.session_state.posiciones:
            nueva_pos = {'precio': precio, 'monto': monto_por_rejilla, 'nivel': 1}
            st.session_state.posiciones.append(nueva_pos)
            st.session_state.saldo -= monto_trade_neto
            evento = "🛒 NIVEL 1 OPEN"
        
        # Lógica para niveles siguientes
        elif len(st.session_state.posiciones) < niveles_max:
            # Calculamos el precio necesario para el siguiente nivel
            ultimo_precio_compra = st.session_state.posiciones[-1]['precio']
            precio_disparo = ultimo_precio_compra * (1 - distancia_grid)
            
            if precio <= precio_disparo:
                nueva_pos = {'precio': precio, 'monto': monto_por_rejilla, 'nivel': len(st.session_state.posiciones)+1}
                st.session_state.posiciones.append(nueva_pos)
                st.session_state.saldo -= monto_trade_neto
                evento = f"🛒 NIVEL {len(st.session_state.posiciones)} OPEN"

        # ... (Resto del código de venta y gráfico)

        # Dibujar líneas de niveles futuros (Previsión)
        if len(st.session_state.posiciones) < niveles_max:
            proximo_buy = st.session_state.posiciones[-1]['precio'] * (1 - distancia_grid)
            fig.add_hline(y=proximo_buy, line_dash="dot", line_color="red", annotation_text="PRÓXIMA COMPRA")
                
