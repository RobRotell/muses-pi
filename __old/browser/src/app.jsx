import { useState, useEffect } from 'preact/hooks'
import styles from './app.module.css'


export const App = () => {
	const [ prompt, setPrompt ] = useState( '' )
	const [ imageUrl, setImageUrl ] = useState( '' )


	useEffect( () => {
		fetch( 'https://muses.robr.app/entry' )
			.then( res => res.json() )
			.then( ({ prompt, images: { small: imageUrl } }) => {
				setPrompt( prompt )
				setImageUrl( imageUrl )
			})
	}, [] )


	return (
		<section className={ styles.container }>
			<img className={ styles.img }
				src={ imageUrl }
			/>
			<div className={ styles.promptContainer }>
				{ prompt }
			</div>
		</section>
	)
}
