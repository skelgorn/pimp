                    # Se não encontrou letras, emite o sinal com o texto atual
                    self.lyrics_data_ready.emit({'text': self.current_lyrics_text, 'parsed': self.parsed_lyrics, 'progress': progress_ms})

                    if lyrics_found:
                        continue

                    time.sleep(1)
                    continue
